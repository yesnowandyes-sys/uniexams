#!/usr/bin/env python3
"""
verify-openai.py — Verify ESAT question enrichment data using OpenAI API.

For each question with stale or missing verification, sends the question +
enrichment to gpt-4.1-mini and asks it to verify correctness of:
  - Solution and worked answer
  - Option references
  - Classification
  - Difficulty rating
  - Formatting (LaTeX, markdown)

Updates the `verification` field inside the enrichment JSON in questions.db.

Usage:
    python3 verify-openai.py                          # verify all stale
    python3 verify-openai.py --question-id ENGAA-2016-S1-Q30
    python3 verify-openai.py --limit 5               # test with 5
    python3 verify-openai.py --dry-run                # list only

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
MAX_TOKENS = 16384
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0
INTER_CALL_DELAY_S = 1.0

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

VERIFY_SYSTEM_PROMPT = """\
You are a meticulous QA reviewer for ESAT (Engineering and Science Admissions \
Test) question enrichment data. You are given ONE question with its enrichment.

Verify the following:
1. **Solution correctness**: Does the worked solution arrive at the stated \
   correct answer? Check every step of the math and logic.
2. **Option references**: Are all option letters (A, B, C, D, etc.) \
   referenced correctly in the solution and distractor analysis? No missing, \
   swapped, or mislabeled letters?
3. **Classification**: Is the topic classification sensible for the content?
4. **Difficulty**: Is the difficulty rating (1-10) reasonable for this question?
5. **Formatting**: Any LaTeX errors, broken markdown sections, or formatting issues?

Output ONLY a JSON object (no markdown fences, no commentary):
{
  "verified": true/false,
  "issues": ["list of specific issues if any"],
  "verifier_note": "optional brief note"
}

Rules:
- "verified": true means NO issues found.
- "verified": false means at least one genuine issue exists.
- Only report genuine issues — do not nitpick style preferences.
- Numerical convention: g = 10 N/kg (ESAT spec).
"""

VERIFY_USER_TEMPLATE = """\
Verify the following ESAT question enrichment.

## QUESTION

ID: {question_id}
Subject: {subject}
Module: {module}

Question text:
{question_text}

Options:
{options_block}

Correct answer: {correct_answer}

## ENRICHMENT DATA

Difficulty rating: {difficulty_rating}
Difficulty category: {difficulty_category}
Topic classification: {topic_classification}

### Enrichment markdown:
{markdown}

## INSTRUCTION

Check the enrichment for correctness. Return ONLY a JSON object:
{{"verified": true/false, "issues": [...], "verifier_note": "..."}}
"""

logger = logging.getLogger("verify-openai")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_api_key(cli_key: str | None) -> str:
    key = (
        cli_key
        or os.environ.get("OPENAI_API_KEY")
        or (KEY_FILE.read_text().strip() if KEY_FILE.is_file() else "")
    )
    if not key:
        logger.error("No OpenAI API key found. Set OPENAI_API_KEY env var or create %s", KEY_FILE)
        sys.exit(1)
    return key


def _format_options(options: Any) -> str:
    if isinstance(options, dict):
        if not options:
            return "(none)"
        return "\n".join(f"  {k}: {v}" for k, v in options.items())
    if isinstance(options, list):
        return "\n".join(f"  {i+1}: {v}" for i, v in enumerate(options))
    return str(options)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Pull a single JSON object out of an LLM response."""
    # Try direct parse first
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try extracting from markdown code block
    code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    # Fallback: find first { ... last }
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        return None
    raw = match.group()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def fetch_questions_to_verify(
    db: sqlite3.Connection,
    question_id: str | None = None,
    stale_only: bool = True,
) -> list[dict[str, Any]]:
    """Fetch questions needing verification.

    If stale_only, only get questions where verification is missing or stale
    (verified=false or no verification field).
    If question_id is given, fetch just that one.
    """
    db.row_factory = sqlite3.Row

    if question_id:
        rows = db.execute(
            """SELECT id, exam_type, year, paper, module, section, subject,
                      question_number, question_text, options, correct_answer, enrichment
               FROM questions WHERE id = ?""",
            (question_id,),
        ).fetchall()
    elif stale_only:
        rows = db.execute(
            """SELECT id, exam_type, year, paper, module, section, subject,
                      question_number, question_text, options, correct_answer, enrichment
               FROM questions
               WHERE enrichment IS NOT NULL
                 AND (
                   json_extract(enrichment, '$.verification.verified') IS NULL
                   OR json_extract(enrichment, '$.verification.verified') = 0
                 )
               ORDER BY id""",
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT id, exam_type, year, paper, module, section, subject,
                      question_number, question_text, options, correct_answer, enrichment
               FROM questions
               WHERE enrichment IS NOT NULL
               ORDER BY id""",
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


def call_verify(
    client: openai.OpenAI,
    question: dict[str, Any],
    model: str,
) -> dict[str, Any] | None:
    """Ask OpenAI to verify one question's enrichment. Returns verification dict."""
    enrichment = question.get("enrichment") or {}

    user_prompt = VERIFY_USER_TEMPLATE.format(
        question_id=question.get("id", "unknown"),
        subject=question.get("subject") or "?",
        module=question.get("module") or "?",
        question_text=(question.get("question_text") or "").strip()[:2000],
        options_block=_format_options(question.get("options")),
        correct_answer=question.get("correct_answer", ""),
        difficulty_rating=enrichment.get("difficulty_rating", "?"),
        difficulty_category=enrichment.get("difficulty_category", "?"),
        topic_classification=json.dumps(enrichment.get("topic_classification", {}), ensure_ascii=False),
        markdown=enrichment.get("markdown", "")[:4000],
    )

    messages = [
        {"role": "system", "content": VERIFY_SYSTEM_PROMPT},
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
                # Ensure required fields
                obj.setdefault("verified", False)
                obj.setdefault("issues", [])
                obj["verified_at"] = datetime.now(timezone.utc).isoformat()
                obj["model"] = model
                # Track token usage
                obj["_input_tokens"] = getattr(resp.usage, "prompt_tokens", 0) or 0
                obj["_output_tokens"] = getattr(resp.usage, "completion_tokens", 0) or 0
                return obj

            logger.warning(
                "Could not parse verify response for %s (attempt %d/%d)",
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

    logger.error("Failed to verify %s after %d retries: %s",
                 question.get("id"), MAX_RETRIES, last_err)
    return None


def update_verification(
    db: sqlite3.Connection,
    question_id: str,
    enrichment: dict[str, Any],
    verification_result: dict[str, Any],
) -> None:
    """Write the verification result into the enrichment JSON in the DB."""
    # Strip internal tracking fields
    v = {k: v2 for k, v2 in verification_result.items() if not k.startswith("_")}
    enrichment["verification"] = v
    db.execute(
        "UPDATE questions SET enrichment = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(enrichment, ensure_ascii=False), question_id),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify ESAT enrichment via OpenAI gpt-4.1-mini.")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N questions")
    parser.add_argument("--question-id", type=str, default=None, help="Verify a specific question")
    parser.add_argument("--all", action="store_true", help="Verify ALL questions, not just stale")
    parser.add_argument("--api-key", type=str, default=None, help="OpenAI API key")
    parser.add_argument("--model", type=str, default=MODEL, help=f"Model (default: {MODEL})")
    parser.add_argument("--dry-run", action="store_true", help="List targets, don't call API")
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
    questions = fetch_questions_to_verify(
        db,
        question_id=args.question_id,
        stale_only=not args.all,
    )
    if args.limit:
        questions = questions[: args.limit]

    logger.info("Found %d questions to verify", len(questions))

    if args.dry_run:
        for q in questions:
            v = q["enrichment"].get("verification", {})
            print(f"{q['id']}  verified={v.get('verified', 'missing')}")
        return

    api_key = get_api_key(args.api_key)
    client = openai.OpenAI(api_key=api_key)

    total = len(questions)
    verified_ok = 0
    verified_fail = 0
    api_errors = 0
    total_input_tokens = 0
    total_output_tokens = 0

    for idx, q in enumerate(questions, start=1):
        qid = q["id"]
        logger.info("[%d/%d] Verifying %s", idx, total, qid)

        result = call_verify(client, q, args.model)

        if result is None:
            api_errors += 1
            logger.warning("[%d/%d] %s — verify FAILED", idx, total, qid)
            time.sleep(INTER_CALL_DELAY_S)
            continue

        total_input_tokens += result.get("_input_tokens", 0)
        total_output_tokens += result.get("_output_tokens", 0)

        update_verification(db, qid, q["enrichment"], result)
        db.commit()

        if result.get("verified"):
            verified_ok += 1
            logger.info("[%d/%d] %s — VERIFIED ✓", idx, total, qid)
        else:
            issues = result.get("issues", [])
            verified_fail += 1
            logger.info("[%d/%d] %s — ISSUES (%d): %s",
                        idx, total, qid, len(issues), "; ".join(issues[:2]))

        time.sleep(INTER_CALL_DELAY_S)

    db.close()

    # Cost estimate (gpt-4.1-mini pricing: $0.40/1M input, $1.60/1M output)
    input_cost = (total_input_tokens / 1_000_000) * 0.40
    output_cost = (total_output_tokens / 1_000_000) * 1.60
    total_cost = input_cost + output_cost

    logger.info("=== verify-openai summary ===")
    logger.info("Total processed: %d / %d", verified_ok + verified_fail + api_errors, total)
    logger.info("  verified OK   : %d", verified_ok)
    logger.info("  issues found  : %d", verified_fail)
    logger.info("  API errors    : %d", api_errors)
    logger.info("  tokens (in/out): %d / %d", total_input_tokens, total_output_tokens)
    logger.info("  est. cost     : $%.4f (in $%.4f + out $%.4f)", total_cost, input_cost, output_cost)


if __name__ == "__main__":
    main()
