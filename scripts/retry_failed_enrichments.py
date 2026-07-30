#!/usr/bin/env python3
"""
Retry failed enrichments directly in the database.

Reads questions with enrichment status "failed" from questions.db,
calls the API (Anthropic SDK via z.ai gateway), and writes the result
back to the database.

Reuses prompt templates and parsing logic from opus-batch-enrichment.py.

Usage:
    python3 retry_failed_enrichments.py --dry-run
    python3 retry_failed_enrichments.py
    python3 retry_failed_enrichments.py --model glm-5.2 --concurrency 2
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import random
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

import anthropic
import importlib.util

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPTS_DIR.parent
DB_PATH = SHARED_DIR / "data" / "questions.db"
TAXONOMY_PATH = SHARED_DIR / "esat_taxonomy.json"
IMAGES_DIR = SHARED_DIR / "corpus" / "images"

# Import reusable functions from opus-batch-enrichment.py (hyphenated name
# requires importlib since Python identifiers can't contain hyphens).
_spec = importlib.util.spec_from_file_location(
    "opus_batch_enrichment", SCRIPTS_DIR / "opus-batch-enrichment.py"
)
assert _spec is not None and _spec.loader is not None
_opus = importlib.util.module_from_spec(_spec)
sys.modules["opus_batch_enrichment"] = _opus  # needed for dataclass introspection
_spec.loader.exec_module(_opus)

SYSTEM_PROMPT_TEMPLATE = _opus.SYSTEM_PROMPT_TEMPLATE
USER_PROMPT_TEMPLATE = _opus.USER_PROMPT_TEMPLATE
NSAA_S2_ACTIVE_RULE = _opus.NSAA_S2_ACTIVE_RULE
load_taxonomy = _opus.load_taxonomy
render_taxonomy_for_module = _opus.render_taxonomy_for_module
parse_enrichment = _opus.parse_enrichment
build_enriched_question = _opus.build_enriched_question
EnrichmentResult = _opus.EnrichmentResult
CorpusFile = _opus.CorpusFile
format_options = _opus.format_options
MAX_RETRIES = _opus.MAX_RETRIES
MAX_IMAGES_PER_QUESTION = _opus.MAX_IMAGES_PER_QUESTION
REQUEST_MAX_TOKENS = _opus.REQUEST_MAX_TOKENS
REQUEST_TIMEOUT_SECONDS = _opus.REQUEST_TIMEOUT_SECONDS
RETRY_BASE_DELAY = _opus.RETRY_BASE_DELAY

logger = logging.getLogger("retry-enrichment")

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def get_failed_questions(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return all questions with enrichment status 'failed'."""
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT id, exam_type, year, paper, module, section, subject,
               question_number, question_text, question_images, options,
               correct_answer
        FROM questions
        WHERE json_extract(enrichment, '$.status') = 'failed'
        ORDER BY id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_questions_by_ids(db: sqlite3.Connection, ids: list[str]) -> list[dict[str, Any]]:
    """Return specific questions by ID (for re-enriching thin/partial records)."""
    db.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in ids)
    rows = db.execute(
        f"""
        SELECT id, exam_type, year, paper, module, section, subject,
               question_number, question_text, question_images, options,
               correct_answer
        FROM questions
        WHERE id IN ({placeholders})
        ORDER BY id
        """,
        ids,
    ).fetchall()
    return [dict(r) for r in rows]


def update_enrichment(
    db: sqlite3.Connection,
    question_id: str,
    enrichment_json: str,
) -> None:
    """Write enrichment JSON back to the database."""
    db.execute(
        "UPDATE questions SET enrichment = ?, updated_at = datetime('now') WHERE id = ?",
        (enrichment_json, question_id),
    )


# ---------------------------------------------------------------------------
# Prompt building (adapted from opus-batch-enrichment.py)
# ---------------------------------------------------------------------------


def detect_source_type(question: dict[str, Any]) -> str:
    """Detect corpus source type from question fields."""
    exam_type = (question.get("exam_type") or "").lower()
    section = (question.get("section") or "").upper()
    if exam_type == "esat":
        return "esat"
    elif exam_type == "engaa":
        return "engaa"
    elif exam_type == "tmua":
        return "tmua"
    elif exam_type == "nsaa":
        if section == "S2":
            return "nsaa_s2"
        return "nsaa"
    return "nsaa"  # fallback


def make_corpus_file(question: dict[str, Any]) -> CorpusFile:
    """Build a CorpusFile from DB question fields for taxonomy lookup."""
    source_type = detect_source_type(question)
    return CorpusFile(
        path=Path(question.get("id", "unknown")),
        source_type=source_type,
        section=question.get("section"),
        subject=question.get("subject"),
        module=question.get("module"),
    )


def build_system_prompt(question: dict[str, Any], taxonomy: dict[str, Any]) -> str:
    cf = make_corpus_file(question)
    block = render_taxonomy_for_module(
        taxonomy,
        source_type=cf.source_type,
        module=cf.module,
        subject=cf.subject,
        section=cf.section,
    )
    rule = NSAA_S2_ACTIVE_RULE if cf.source_type == "nsaa_s2" else ""
    prompt = SYSTEM_PROMPT_TEMPLATE.format(taxonomy_block=block, nsaa_s2_rule=rule)
    if not rule:
        prompt = prompt.replace("\n\n\n\n## OUTPUT FORMAT", "\n\n## OUTPUT FORMAT")
    return prompt


def build_user_prompt(question: dict[str, Any]) -> str:
    qt = question.get("question_text", "") or ""
    options_raw = question.get("options", "{}")
    if isinstance(options_raw, str):
        options = json.loads(options_raw)
    else:
        options = options_raw
    correct = question.get("correct_answer", "") or ""
    return USER_PROMPT_TEMPLATE.format(
        question_text=qt,
        options_list=format_options(options),
        correct_answer_letter=correct,
    )


# ---------------------------------------------------------------------------
# Image handling
# ---------------------------------------------------------------------------


def get_image_paths(question: dict[str, Any]) -> list[str]:
    """Return image paths from the question_images field."""
    raw = question.get("question_images", "[]")
    if isinstance(raw, str):
        paths = json.loads(raw)
    elif isinstance(raw, list):
        paths = raw
    else:
        paths = []
    # Filter to image extensions
    return [p for p in paths if isinstance(p, str) and p.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))]


def build_image_blocks(image_paths: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for rel in image_paths[:MAX_IMAGES_PER_QUESTION]:
        # Try corpus/images/ and shared root
        cands = [IMAGES_DIR / rel, SHARED_DIR / "corpus" / rel, SHARED_DIR / rel]
        abs_path = None
        for c in cands:
            if c.exists():
                abs_path = c
                break
        if abs_path is None:
            logger.warning("Image not found: %s", rel)
            continue
        ext = abs_path.suffix.lower()
        media_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(ext, "image/png")
        with open(abs_path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
        blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        })
    return blocks


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------


def call_api(
    client: anthropic.Anthropic,
    system_prompt: str,
    user_prompt: str,
    model: str,
    image_blocks: Optional[list[dict[str, Any]]] = None,
) -> tuple[str, dict[str, int]]:
    """Call the Messages API with retry. Returns (response_text, token_usage)."""
    content_blocks: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
    if image_blocks:
        content_blocks.extend(image_blocks)

    messages = [{"role": "user", "content": content_blocks}]

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=REQUEST_MAX_TOKENS,
                timeout=REQUEST_TIMEOUT_SECONDS,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
            )
            text = ""
            for block in response.content:
                if getattr(block, "type", "") == "text":
                    text += getattr(block, "text", "")
            usage = {
                "input_tokens": getattr(response.usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(response.usage, "output_tokens", 0) or 0,
                "cache_read_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            }
            return text, usage
        except anthropic.RateLimitError as e:
            last_exc = e
            delay = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1.5)
            logger.warning("Rate limit (attempt %d/%d), retry in %.1fs", attempt + 1, MAX_RETRIES, delay)
            time.sleep(delay)
        except anthropic.APIConnectionError as e:
            last_exc = e
            delay = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1.0)
            logger.warning("Connection error (attempt %d/%d), retry in %.1fs", attempt + 1, MAX_RETRIES, delay)
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            last_exc = e
            if 400 <= e.status_code < 500 and e.status_code != 429:
                raise RuntimeError(f"API {e.status_code}: {getattr(e, 'message', str(e))}") from e
            delay = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1.0)
            logger.warning("API %d (attempt %d/%d), retry in %.1fs", e.status_code, attempt + 1, MAX_RETRIES, delay)
            time.sleep(delay)
        except Exception as e:
            last_exc = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Unexpected error (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
            time.sleep(delay)

    raise RuntimeError(f"Exhausted {MAX_RETRIES} retries: {last_exc}")


# ---------------------------------------------------------------------------
# Per-question processing
# ---------------------------------------------------------------------------


def process_question(
    client: anthropic.Anthropic,
    question: dict[str, Any],
    taxonomy: dict[str, Any],
    model: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Enrich a single question and return the enrichment JSON dict."""
    qid = question["id"]
    system_prompt = build_system_prompt(question, taxonomy)
    user_prompt = build_user_prompt(question)
    image_paths = get_image_paths(question)
    image_blocks = build_image_blocks(image_paths) if image_paths else None

    if dry_run:
        logger.info("[DRY RUN] %s — system prompt %d chars, user prompt %d chars, %d images",
                     qid, len(system_prompt), len(user_prompt), len(image_blocks or []))
        return {"status": "success", "dry_run": True, "id": qid}

    start = time.time()
    logger.info("Enriching %s (%d images)...", qid, len(image_blocks or []))

    try:
        text, usage = call_api(client, system_prompt, user_prompt, model, image_blocks=image_blocks)
    except RuntimeError as e:
        logger.error("FAILED %s: %s", qid, e)
        return {
            "status": "failed",
            "model": model,
            "enriched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "markdown": None,
            "error": str(e),
            "processor_id": model,
            "attempts": MAX_RETRIES,
        }

    duration = time.time() - start
    cf = make_corpus_file(question)
    parsed = parse_enrichment(text, cf)

    result = EnrichmentResult(
        question_id=qid,
        source_file=qid,
        status="success",
        enrichment_markdown=text,
        difficulty_rating=parsed.get("difficulty_rating"),
        difficulty_category=parsed.get("difficulty_category"),
        topic_classification=parsed.get("topic_classification", {}),
        ocr_corrections=parsed.get("ocr_corrections", []),
        error="",
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_read_tokens=usage.get("cache_read_tokens", 0),
        cache_creation_tokens=usage.get("cache_creation_tokens", 0),
        duration_seconds=duration,
        attempts=1,
    )

    enriched_q = build_enriched_question(question, result, model)
    enrichment = enriched_q["enrichment"]
    logger.info("OK %s — %d in / %d out tokens, %.1fs", qid, usage.get("input_tokens", 0), usage.get("output_tokens", 0), duration)
    return enrichment


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry failed enrichments in the database.")
    parser.add_argument("--model", type=str, default="glm-5.2", help="Model name (default: glm-5.2)")
    parser.add_argument("--dry-run", action="store_true", help="Don't call the API; just print what would happen")
    parser.add_argument("--ids", type=str, default=None, help="Comma-separated question IDs to re-enrich (overrides failed-status search)")
    parser.add_argument("--concurrency", type=int, default=2, help="Parallel workers (default: 2)")
    parser.add_argument("--api-key", type=str, default=None, help="API key (or set ANTHROPIC_API_KEY)")
    parser.add_argument("--base-url", type=str, default=None, help="API base URL (or set ANTHROPIC_BASE_URL)")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N questions (testing)")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Load taxonomy
    taxonomy = load_taxonomy(TAXONOMY_PATH)
    logger.info("Loaded taxonomy with %d modules", len(taxonomy.get("modules", [])))

    # Connect DB
    db = sqlite3.connect(str(DB_PATH))
    if args.ids:
        ids = [s.strip() for s in args.ids.split(",") if s.strip()]
        questions = get_questions_by_ids(db, ids)
        logger.info("Found %d questions by ID filter", len(questions))
    else:
        questions = get_failed_questions(db)
        logger.info("Found %d failed enrichments in database", len(questions))

    if args.limit:
        questions = questions[: args.limit]
        logger.info("Limited to %d questions", len(questions))

    if not questions:
        logger.info("Nothing to do — no failed enrichments found.")
        return

    if args.dry_run:
        for q in questions:
            process_question(None, q, taxonomy, args.model, dry_run=True)  # type: ignore
        logger.info("[DRY RUN] Would enrich %d questions", len(questions))
        return

    # Build API client
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    base_url = args.base_url or os.environ.get("ANTHROPIC_BASE_URL")
    if not api_key:
        logger.error("No API key — set ANTHROPIC_API_KEY or pass --api-key")
        sys.exit(1)

    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = anthropic.Anthropic(**client_kwargs)
    logger.info("API client ready (base_url=%s, model=%s)", base_url or "default", args.model)

    # Process with concurrency
    success_count = 0
    fail_count = 0

    if args.concurrency <= 1:
        for q in questions:
            enrichment = process_question(client, q, taxonomy, args.model)
            update_enrichment(db, q["id"], json.dumps(enrichment))
            db.commit()
            if enrichment.get("status") == "success":
                success_count += 1
            else:
                fail_count += 1
    else:
        results: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {
                pool.submit(process_question, client, q, taxonomy, args.model): q["id"]
                for q in questions
            }
            for future in as_completed(futures):
                qid = futures[future]
                try:
                    results[qid] = future.result()
                except Exception as e:
                    logger.error("UNEXPECTED %s: %s", qid, e)
                    results[qid] = {
                        "status": "failed",
                        "model": args.model,
                        "enriched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "markdown": None,
                        "error": f"Unexpected: {e}",
                        "processor_id": args.model,
                    }

        # Write all results to DB
        for qid, enrichment in results.items():
            update_enrichment(db, qid, json.dumps(enrichment))
            if enrichment.get("status") == "success":
                success_count += 1
            else:
                fail_count += 1
        db.commit()

    db.close()
    logger.info("Done: %d success, %d failed (out of %d)", success_count, fail_count, len(questions))


if __name__ == "__main__":
    main()
