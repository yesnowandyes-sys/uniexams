#!/usr/bin/env python3
"""
Batch verification pipeline for all enriched questions.

Reads enriched questions from questions.db, sends them in batches to
GLM-5.2 for verification (solution correctness, option references,
classification, difficulty, formatting), and stores the results in the
enrichment JSON's "verification" field.

Reuses verification prompts/logic from glm-enrichment.py.

Usage:
    python3 batch_verify.py --dry-run
    python3 batch_verify.py --batch-size 100
    python3 batch_verify.py --batch-size 50 --limit 200
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import openai

SCRIPTS_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPTS_DIR.parent
DB_PATH = SHARED_DIR / "data" / "questions.db"

# Import verification logic from glm-enrichment.py
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "glm_enrichment", SCRIPTS_DIR / "glm-enrichment.py"
)
assert _spec is not None and _spec.loader is not None
_glm = importlib.util.module_from_spec(_spec)
sys.modules["glm_enrichment"] = _glm
_spec.loader.exec_module(_glm)

VERIFICATION_SYSTEM_PROMPT = _glm.VERIFICATION_SYSTEM_PROMPT
VERIFICATION_BATCH_TEMPLATE = _glm.VERIFICATION_BATCH_TEMPLATE
_extract_verification_context = _glm._extract_verification_context
_format_verification_batch = _glm._format_verification_batch

ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
DEFAULT_MODEL = "glm-5.2"
MAX_RETRIES = 5
RETRY_BASE_DELAY = 3.0

logger = logging.getLogger("batch-verify")


def get_enriched_questions(db: sqlite3.Connection, limit: int | None = None, skip_verified: bool = False) -> list[dict[str, Any]]:
    """Return all questions with successful enrichment, ready for verification."""
    db.row_factory = sqlite3.Row
    skip_clause = "AND json_extract(enrichment, '$.verification.verified') IS NULL" if skip_verified else ""
    query = f"""
        SELECT id, exam_type, year, paper, module, section, subject,
               question_number, question_text, question_images, options,
               correct_answer, enrichment
        FROM questions
        WHERE json_extract(enrichment, '$.status') IN ('success', 'out_of_spec')
        {skip_clause}
        ORDER BY id
    """
    if limit:
        query += f" LIMIT {limit}"
    rows = db.execute(query).fetchall()
    questions = []
    for r in rows:
        q = dict(r)
        q["enrichment"] = json.loads(q["enrichment"]) if q["enrichment"] else {}
        # Parse options if string
        if isinstance(q.get("options"), str):
            q["options"] = json.loads(q["options"])
        questions.append(q)
    return questions


def _parse_json_lenient(text: str) -> list[dict[str, Any]] | None:
    """Try multiple strategies to extract a JSON array from LLM output."""
    # Strategy 1: direct regex for JSON array
    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    if json_match:
        raw = json_match.group()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # Strategy 2: fix common issues — unescaped control chars in strings
        try:
            # Remove literal control characters that break JSON
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        # Strategy 3: try parsing individual objects from the array
        try:
            objects = re.findall(r'\{[^{}]+\}', raw)
            results = []
            for obj_str in objects:
                cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', obj_str)
                results.append(json.loads(cleaned))
            if results:
                return results
        except (json.JSONDecodeError, Exception):
            pass
    return None


def verify_batch(
    client: openai.OpenAI,
    items: list[dict[str, Any]],
    model: str,
) -> list[dict[str, Any]]:
    """Send a batch of questions to GLM for verification."""
    if not items:
        return []

    batch_content = _format_verification_batch(items)
    user_prompt = VERIFICATION_BATCH_TEMPLATE.format(
        count=len(items),
        batch_content=batch_content,
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": VERIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=32768,
                messages=messages,
            )
            response_text = response.choices[0].message.content or ""

            # Extract JSON array from response using lenient parser
            results = _parse_json_lenient(response_text)
            if results:
                logger.info("Verified %d questions (got %d results)", len(items), len(results))
                return results
            else:
                logger.warning("Verification: could not parse JSON from response (attempt %d)", attempt + 1)
                logger.debug("Response (first 300 chars): %s", response_text[:300])
        except openai.RateLimitError as e:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Rate limit (attempt %d/%d), retry in %.1fs", attempt + 1, MAX_RETRIES, delay)
            time.sleep(delay)
        except Exception as e:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Error (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
            time.sleep(delay)

    logger.error("Failed to verify batch after %d retries", MAX_RETRIES)
    return [{"question_id": item["question_id"], "verified": False, "issues": ["Verification API failed"]} for item in items]


def update_verification(
    db: sqlite3.Connection,
    question_id: str,
    verification_result: dict[str, Any],
) -> None:
    """Write verification result into the enrichment JSON."""
    row = db.execute("SELECT enrichment FROM questions WHERE id = ?", (question_id,)).fetchone()
    if not row:
        return
    enrichment = json.loads(row[0])
    enrichment["verification"] = {
        "verified": verification_result.get("verified", False),
        "issues": verification_result.get("issues", []),
    }
    db.execute(
        "UPDATE questions SET enrichment = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(enrichment), question_id),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch verification of enriched questions.")
    parser.add_argument("--batch-size", type=int, default=100, help="Questions per verification batch (default: 100)")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N questions (testing)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--api-key", type=str, default=None, help="API key (or set ANTHROPIC_API_KEY)")
    parser.add_argument("--base-url", type=str, default=ZAI_BASE_URL, help="API base URL")
    parser.add_argument("--skip-verified", action="store_true", help="Skip questions that already have verification data")
    parser.add_argument("--dry-run", action="store_true", help="Don't call API; just print batches")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    db = sqlite3.connect(str(DB_PATH))
    questions = get_enriched_questions(db, limit=args.limit, skip_verified=args.skip_verified)
    logger.info("Loaded %d enriched questions for verification", len(questions))

    if not questions:
        logger.info("Nothing to verify.")
        return

    # Prepare verification items
    items = []
    for q in questions:
        try:
            item = _extract_verification_context(q)
            items.append(item)
        except Exception as e:
            logger.warning("Failed to extract verification context for %s: %s", q.get("id"), e)

    logger.info("Prepared %d verification items", len(items))

    # Batch them
    batches = [items[i:i + args.batch_size] for i in range(0, len(items), args.batch_size)]
    logger.info("Split into %d batches of up to %d questions", len(batches), args.batch_size)

    if args.dry_run:
        for i, batch in enumerate(batches):
            logger.info("[DRY RUN] Batch %d: %d questions (%s ... %s)",
                        i + 1, len(batch),
                        batch[0]["question_id"], batch[-1]["question_id"])
        logger.info("[DRY RUN] Would verify %d questions in %d batches", len(items), len(batches))
        return

    # Build API client
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("No API key — set ANTHROPIC_API_KEY or pass --api-key")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key, base_url=args.base_url)
    logger.info("API client ready (base_url=%s, model=%s)", args.base_url, args.model)

    # Process batches
    total_verified = 0
    total_with_issues = 0
    total_failed = 0

    for i, batch in enumerate(batches):
        batch_start = time.time()
        logger.info("Processing batch %d/%d (%d questions: %s ... %s)",
                     i + 1, len(batches), len(batch),
                     batch[0]["question_id"], batch[-1]["question_id"])

        results = verify_batch(client, batch, args.model)

        for result in results:
            qid = result.get("question_id", "")
            verified = result.get("verified", False)
            issues = result.get("issues", [])

            update_verification(db, qid, result)

            if verified:
                total_verified += 1
            elif issues:
                total_with_issues += 1
            else:
                total_failed += 1

        db.commit()
        elapsed = time.time() - batch_start
        logger.info("Batch %d done in %.1fs — running totals: %d verified, %d with issues, %d failed",
                     i + 1, elapsed, total_verified, total_with_issues, total_failed)

    db.close()
    logger.info("=== Verification complete ===")
    logger.info("Total: %d verified, %d with issues, %d failed (out of %d)",
                total_verified, total_with_issues, total_failed, len(items))


if __name__ == "__main__":
    main()
