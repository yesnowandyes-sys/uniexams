#!/usr/bin/env python3
"""
fix-openai.py — Fix unverified ESAT questions using OpenAI gpt-4.1-mini.

For each question where enrichment.verification.verified == false:
1. Sends the question + current enrichment + flagged issues to gpt-4.1-mini
2. Gets back corrected enrichment JSON
3. Immediately re-verifies the fixed enrichment
4. Writes the result back to questions.db

Resumable: only processes questions still marked unverified.

Usage:
    python3 fix-openai.py --dry-run          # list targets
    python3 fix-openai.py --limit 5          # test with 5
    python3 fix-openai.py                    # full run

Environment:
    OPENAI_API_KEY — or fallback file at scripts/.openai-api-key
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openai

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPTS_DIR.parent
DB_PATH = SHARED_DIR / "data" / "questions.db"
KEY_FILE = SCRIPTS_DIR / ".openai-api-key"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MODEL = "gpt-4.1-mini"
MAX_TOKENS = 32768
MAX_RETRIES = 4
RETRY_BASE_DELAY = 2.0
INTER_CALL_DELAY_S = 1.0  # 1-second delay between calls (OpenAI is pay-per-use)

# Import verify functions from verify-openai.py (same directory)
# The filename uses a hyphen, so we use importlib instead of a normal import
import importlib.util
_verify_spec = importlib.util.spec_from_file_location(
    "verify_openai", SCRIPTS_DIR / "verify-openai.py"
)
assert _verify_spec is not None and _verify_spec.loader is not None
_verify_mod = importlib.util.module_from_spec(_verify_spec)
sys.modules["verify_openai"] = _verify_mod
_verify_spec.loader.exec_module(_verify_mod)

call_verify = _verify_mod.call_verify
get_api_key = _verify_mod.get_api_key
_format_options = _verify_mod._format_options
_extract_json_object = _verify_mod._extract_json_object

# ---------------------------------------------------------------------------
# Fix prompts
# ---------------------------------------------------------------------------

FIX_SYSTEM_PROMPT = """\
You are an expert Cambridge admissions test analyst specialising in the \
Engineering and Science Admissions Test (ESAT). You are given ONE previously \
enriched question along with a list of specific QA issues that a reviewer \
flagged in its enrichment data.

Your job: rewrite the enrichment so the flagged issues are resolved. Use \
the same JSON schema and the same field names as the input enrichment. \
Return ONLY the corrected enrichment JSON object — no commentary, no \
markdown fences.

## NUMERICAL CONVENTIONS

- Gravitational field strength: g = 10 N/kg (ESAT convention).
- Use only standard angles: 0, 30, 45, 60, 90 degrees (and multiples).
- All physical constants not listed in the ESAT specification MUST be given \
  in the question stem.

## OUTPUT SCHEMA

Return a single JSON object with EXACTLY these keys:
{
  "status": "success" | "out_of_spec",
  "model": "gpt-4.1-mini",
  "enriched_at": "<ISO 8601 UTC timestamp>",
  "markdown": "<full enrichment markdown>",
  "difficulty_rating": <integer 1-10>,
  "difficulty_category": "<string>",
  "topic_classification": {"module": "...", "module_code": "...", "topic_code": "...", "topic_name": "...", "content_code": "...", "question_type": "...", "is_out_of_spec": false},
  "ocr_corrections": <object or null>,
  "error": null,
  "processor_id": "fix-openai-gpt-4.1-mini",
  "input_tokens": <integer>,
  "output_tokens": <integer>,
  "attempts": <integer>,
  "duration_seconds": <number>
}

## MARKDOWN STRUCTURE (CRITICAL — verifier requires this exact format)

The "markdown" field MUST use level-2 (`##`) headers, NOT level-1 (`#`).

Use this exact section order:

## Worked Solution
<step-by-step solution with LaTeX maths, arriving at the stated correct answer>

## Distractor Analysis
<for each incorrect option, one sentence explaining why it is wrong>

## Classification
<module, topic name, and content code from the ESAT specification>

## Difficulty Rating
<rating from 1 to 10 with a one-line justification>

## Diagram Descriptions
<if the question references a diagram, describe it; otherwise omit>

Rules:
- LaTeX only for maths: `$...$` inline, `$$...$$` display.
- Every section EXCEPT Diagram Descriptions MUST be non-empty.
- Preserve any correct content from the input enrichment; only fix what is wrong.
- Do NOT include a "verification" field — it is managed separately.
- Output is a SINGLE JSON object, nothing else. No markdown fences, no prose.
"""

FIX_USER_TEMPLATE = """\
Fix the flagged issues in the enrichment below.

## ORIGINAL QUESTION

Question ID: {question_id}
Subject / Module: {subject} / {module}
Question text:
{question_text}

Options:
{options_block}

Correct answer: {correct_answer}

## CURRENT ENRICHMENT (may contain errors)

{current_enrichment_json}

## FLAGGED ISSUES TO FIX

{issues_block}

## INSTRUCTION

Rewrite the enrichment so the issues above are resolved. Return ONLY the \
corrected JSON object, same schema as the input enrichment (minus the \
"verification" field, which is managed separately). Do not add any text \
before or after the JSON.
"""

logger = logging.getLogger("fix-openai")

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def fetch_unverified(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """All questions with verified=false AND at least one issue."""
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT id, exam_type, year, paper, module, section, subject,
               question_number, question_text, options, correct_answer, enrichment
        FROM questions
        WHERE enrichment IS NOT NULL
          AND json_extract(enrichment, '$.verification.verified') = 0
          AND json_array_length(json_extract(enrichment, '$.verification.issues')) > 0
        ORDER BY id
        """
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        q = dict(r)
        try:
            q["enrichment"] = json.loads(q["enrichment"]) if q["enrichment"] else {}
        except json.JSONDecodeError:
            q["enrichment"] = {}
        try:
            q["options"] = json.loads(q["options"]) if isinstance(q.get("options"), str) else (q.get("options") or {})
        except json.JSONDecodeError:
            q["options"] = {}
        out.append(q)
    return out


def write_enrichment(db: sqlite3.Connection, question_id: str, enrichment: dict[str, Any]) -> None:
    db.execute(
        "UPDATE questions SET enrichment = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(enrichment, ensure_ascii=False), question_id),
    )


# ---------------------------------------------------------------------------
# Fix call
# ---------------------------------------------------------------------------


def call_fix(
    client: openai.OpenAI,
    question: dict[str, Any],
    model: str,
) -> tuple[dict[str, Any] | None, int, int]:
    """Ask OpenAI to return a corrected enrichment for one question.

    Returns (corrected_enrichment_or_None, input_tokens, output_tokens).
    """
    enrichment = question.get("enrichment") or {}
    issues = enrichment.get("verification", {}).get("issues", []) or []

    issues_block = "\n".join(f"- {issue}" for issue in issues) or "- (no specific issues listed)"

    user_prompt = FIX_USER_TEMPLATE.format(
        question_id=question.get("id", "unknown"),
        subject=question.get("subject") or "?",
        module=question.get("module") or "?",
        question_text=(question.get("question_text") or "").strip()[:2000],
        options_block=_format_options(question.get("options")),
        correct_answer=question.get("correct_answer", ""),
        current_enrichment_json=json.dumps(enrichment, ensure_ascii=False, indent=2),
        issues_block=issues_block,
    )

    messages = [
        {"role": "system", "content": FIX_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=MAX_TOKENS,
                messages=messages,
            )
            text = resp.choices[0].message.content or ""
            obj = _extract_json_object(text)
            if obj is not None:
                # Stamp bookkeeping fields
                obj.setdefault("status", "success")
                obj["model"] = model
                obj["enriched_at"] = datetime.now(timezone.utc).isoformat()
                obj["processor_id"] = "fix-openai-gpt-4.1-mini"
                obj.setdefault("attempts", enrichment.get("attempts", 0))
                if isinstance(obj.get("attempts"), int):
                    obj["attempts"] = obj["attempts"] + 1
                obj.setdefault("input_tokens", getattr(resp.usage, "prompt_tokens", 0) or 0)
                obj.setdefault("output_tokens", getattr(resp.usage, "completion_tokens", 0) or 0)
                obj.setdefault("duration_seconds", 0.0)
                obj.pop("verification", None)  # never trust model-supplied verification
                in_tok = getattr(resp.usage, "prompt_tokens", 0) or 0
                out_tok = getattr(resp.usage, "completion_tokens", 0) or 0
                return obj, in_tok, out_tok

            logger.warning(
                "Could not parse JSON fix response for %s (attempt %d/%d)",
                question.get("id"), attempt + 1, MAX_RETRIES,
            )
        except openai.RateLimitError as e:
            last_err = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Rate limit (attempt %d/%d) for %s — retry in %.1fs",
                           attempt + 1, MAX_RETRIES, question.get("id"), delay)
            time.sleep(delay)
        except Exception as e:
            last_err = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("API error (attempt %d/%d) for %s: %s",
                           attempt + 1, MAX_RETRIES, question.get("id"), e)
            time.sleep(delay)

    logger.error("Failed to fix %s after %d retries: %s",
                 question.get("id"), MAX_RETRIES, last_err)
    return None, 0, 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix unverified ESAT questions via OpenAI gpt-4.1-mini.")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N questions")
    parser.add_argument("--api-key", type=str, default=None, help="OpenAI API key")
    parser.add_argument("--model", type=str, default=MODEL, help=f"Model (default: {MODEL})")
    parser.add_argument("--dry-run", action="store_true", help="List targets, don't call API")
    parser.add_argument("--skip-reverify", action="store_true", help="Skip re-verification after fix")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    if not DB_PATH.exists():
        logger.error("DB not found at %s", DB_PATH)
        sys.exit(1)

    db = sqlite3.connect(str(DB_PATH))
    questions = fetch_unverified(db)
    if args.limit:
        questions = questions[: args.limit]

    logger.info("Found %d unverified questions to fix", len(questions))

    if args.dry_run:
        for q in questions:
            issues = q["enrichment"].get("verification", {}).get("issues", [])
            print(f"{q['id']}  issues={len(issues)}")
        logger.info("[DRY RUN] Would fix %d questions", len(questions))
        return

    api_key = get_api_key(args.api_key)
    client = openai.OpenAI(api_key=api_key)

    total = len(questions)
    fixed_ok = 0           # fix applied AND re-verify passed
    fixed_but_failing = 0  # fix applied but re-verify still has issues
    fix_failed = 0         # fix API call failed

    # Token tracking
    total_fix_input = 0
    total_fix_output = 0
    total_verify_input = 0
    total_verify_output = 0

    for idx, q in enumerate(questions, start=1):
        qid = q["id"]
        issues = q["enrichment"].get("verification", {}).get("issues", []) or []
        logger.info("[%d/%d] %s — %d issue(s)", idx, total, qid, len(issues))
        for issue in issues:
            logger.info("  issue: %s", issue)

        # ---- Step 1: Fix the enrichment ---------------------------------
        t0 = time.time()
        new_enrichment, fix_in, fix_out = call_fix(client, q, args.model)
        elapsed = time.time() - t0

        if new_enrichment is None:
            fix_failed += 1
            logger.warning("[%d/%d] %s — fix FAILED", idx, total, qid)
            time.sleep(INTER_CALL_DELAY_S)
            continue

        total_fix_input += fix_in
        total_fix_output += fix_out
        try:
            new_enrichment["duration_seconds"] = round(elapsed, 3)
        except Exception:
            pass

        time.sleep(INTER_CALL_DELAY_S)

        # ---- Step 2: Re-verify the fixed enrichment ----------------------
        if args.skip_reverify:
            new_enrichment["verification"] = {
                "verified": True,
                "issues": [],
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "verifier_note": "skipped",
            }
            verify_in = verify_out = 0
        else:
            # Build a question dict with the new enrichment for verification
            verify_q = dict(q)
            verify_q["enrichment"] = new_enrichment
            vresult = call_verify(client, verify_q, args.model)
            if vresult is not None:
                verify_in = vresult.get("_input_tokens", 0)
                verify_out = vresult.get("_output_tokens", 0)
                # Write verification into enrichment
                v = {k: v2 for k, v2 in vresult.items() if not k.startswith("_")}
                new_enrichment["verification"] = v
            else:
                verify_in = verify_out = 0
                new_enrichment["verification"] = {
                    "verified": False,
                    "issues": ["re-verify API call failed"],
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "model": args.model,
                }

        total_verify_input += verify_in
        total_verify_output += verify_out

        # ---- Step 3: Persist --------------------------------------------
        write_enrichment(db, qid, new_enrichment)
        db.commit()

        v = new_enrichment.get("verification", {})
        verified = bool(v.get("verified", False))
        remaining_issues = v.get("issues", []) or []
        if verified:
            fixed_ok += 1
            logger.info("[%d/%d] %s — FIXED & VERIFIED ✓", idx, total, qid)
        else:
            fixed_but_failing += 1
            logger.info(
                "[%d/%d] %s — fix applied but still unverified (%d remaining issue(s))",
                idx, total, qid, len(remaining_issues),
            )

        time.sleep(INTER_CALL_DELAY_S)

    db.close()

    # Cost estimate (gpt-4.1-mini: $0.40/1M input, $1.60/1M output)
    all_input = total_fix_input + total_verify_input
    all_output = total_fix_output + total_verify_output
    input_cost = (all_input / 1_000_000) * 0.40
    output_cost = (all_output / 1_000_000) * 1.60
    total_cost = input_cost + output_cost

    logger.info("=== fix-openai summary ===")
    logger.info("Total processed this run : %d / %d", fixed_ok + fixed_but_failing + fix_failed, total)
    logger.info("  fixed & verified        : %d", fixed_ok)
    logger.info("  fixed but still failing : %d", fixed_but_failing)
    logger.info("  fix API failures        : %d", fix_failed)
    logger.info("  --- token usage ---")
    logger.info("  fix tokens (in/out)     : %d / %d", total_fix_input, total_fix_output)
    logger.info("  verify tokens (in/out)  : %d / %d", total_verify_input, total_verify_output)
    logger.info("  total tokens (in/out)   : %d / %d", all_input, all_output)
    logger.info("  est. cost               : $%.4f (in $%.4f + out $%.4f)", total_cost, input_cost, output_cost)


if __name__ == "__main__":
    main()
