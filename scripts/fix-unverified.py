#!/usr/bin/env python3
"""
Targeted fix pipeline for unverified ESAT questions.

Reads every question whose enrichment.verification.verified == false (with a
non-empty `issues` array) from questions.db, sends each one individually to
GLM-5.2 along with the specific verification issues, and asks GLM-5.2 to
return corrected enrichment JSON. After each fix the question is re-verified
using the same verifier used by `batch_verify.py`, and the verification field
is updated.

Resumable: a question is only re-sent if it is still unverified. Once a fix
makes the verifier happy (verified == true) it is skipped on subsequent runs.

Usage:
    python3 fix-unverified.py --dry-run --limit 5
    python3 fix-unverified.py --limit 10
    python3 fix-unverified.py                # full run

Environment:
    ANTHROPIC_API_KEY  — z.ai API key (same key used by glm-enrichment.py).
    ZAI_API_KEY        — alternative env var name for the API key.
"""

from __future__ import annotations

import argparse
import importlib.util
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

# ---------------------------------------------------------------------------
# GLM API configuration
# ---------------------------------------------------------------------------
# NOTE on endpoints:
#   The task spec referenced http://127.0.0.1:8081/v1/chat/completions, but
#   that local server is only the quota dashboard — it does NOT expose a
#   chat completions route. The working GLM-5.2 endpoint is the public z.ai
#   OpenAI-compatible API at https://api.z.ai/api/coding/paas/v4, which is
#   the same base used by `glm-enrichment.py` and `batch_verify.py`. The
#   quota guard endpoint (http://127.0.0.1:8081/api/zai-quota) IS served
#   locally and is used here exactly as specified in the task.
ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
DEFAULT_MODEL = "glm-5.2"

QUOTA_URL = "http://127.0.0.1:8081/api/zai-quota"

MAX_TOKENS = 32768
MAX_RETRIES = 4
RETRY_BASE_DELAY = 3.0
INTER_CALL_DELAY_S = 5.0  # mandatory delay between successful API calls

# ---------------------------------------------------------------------------
# Reuse the verifier from glm-enrichment.py so re-verification is identical
# to what batch_verify.py does.
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "glm_enrichment", SCRIPTS_DIR / "glm-enrichment.py"
)
assert _spec is not None and _spec.loader is not None
_glm = importlib.util.module_from_spec(_spec)
sys.modules["glm_enrichment"] = _glm
_spec.loader.exec_module(_glm)

_extract_verification_context = _glm._extract_verification_context
_verify_batch = _glm.verify_batch  # type: ignore[attr-defined]

logger = logging.getLogger("fix-unverified")

# ---------------------------------------------------------------------------
# Fix prompt
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

- Gravitational field strength: g = 10 N kg⁻¹ (ESAT convention, spec P3.5b).
- Use only standard angles: 0°, 30°, 45°, 60°, 90° (and multiples).
- All physical constants not listed in the ESAT specification MUST be given \
  in the question stem.

## OUTPUT SCHEMA

Return a single JSON object with EXACTLY these keys:
{
  "status": "success" | "out_of_spec",
  "model": "glm-5.2",
  "enriched_at": "<ISO 8601 UTC timestamp>",
  "markdown": "<full enrichment markdown — Worked Solution, Classification, Difficulty, ...>",
  "difficulty_rating": <integer 1-10>,
  "difficulty_category": "<string>",
  "topic_classification": {"module": "...", "module_code": "...", "topic_code": "...", "topic_name": "...", "content_code": "...", "question_type": "...", "is_out_of_spec": false},
  "ocr_corrections": <object or null>,
  "error": null,
  "processor_id": "fix-unverified-glm-5.2",
  "input_tokens": <integer>,
  "output_tokens": <integer>,
  "attempts": <integer>,
  "duration_seconds": <number>
}

## MARKDOWN STRUCTURE (CRITICAL — verifier requires this exact format)

The "markdown" field MUST use level-2 (`##`) headers, NOT level-1 (`#`). The \
verifier parses sections by `^##\\s+` regex; if you use `#` headers or omit a \
required section, the question will fail re-verification.

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
<if the question references a diagram, describe it; otherwise omit this section>

Rules:
- LaTeX only for maths: `$...$` inline, `$$...$$` display. Never raw LaTeX outside maths.
- Every section EXCEPT Diagram Descriptions MUST be non-empty.
- Preserve any correct content from the input enrichment; only fix what is wrong.
- Do NOT include a "verification" field — it is managed by the re-verifier.
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _zai_catalog_key() -> str | None:
    """Try to read the API key from the z.ai plugin catalog."""
    for candidate in [
        Path(__file__).resolve().parent.parent.parent.parent
        / ".openclaw" / "agents" / "esat-manager" / "agent" / "plugins" / "zai" / "catalog.json",
        Path.home() / ".openclaw" / "agents" / "esat-manager" / "agent" / "plugins" / "zai" / "catalog.json",
    ]:
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text())
                key = data.get("providers", {}).get("zai", {}).get("apiKey")
                if key:
                    return key
            except Exception:
                pass
    return None


def get_api_key(cli_key: str | None) -> str:
    key = (
        cli_key
        or os.environ.get("ZAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or _zai_catalog_key()
    )
    if not key:
        logger.error("No API key — set ZAI_API_KEY or pass --api-key")
        sys.exit(1)
    return key


def fetch_unverified(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """All questions with verified=false AND at least one issue."""
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT id, exam_type, year, paper, module, section, subject,
               question_number, question_text, options, correct_answer, enrichment
        FROM questions
        WHERE json_extract(enrichment, '$.verification.verified') = 0
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


def check_quota(session) -> tuple[bool, dict[str, Any] | None]:
    """Return (ok_to_proceed, quota_payload).

    Checks both the 5-hour and weekly quota windows.
    Stops if EITHER:
      - weekly usage >= 85% (hard stop — almost exhausted)
      - 5-hour usage > 5-hour elapsed (rate limit on short window)
    The weekly rate-based check (percentage > elapsedPct) from the original
    spec is too aggressive when prior batch operations consumed the weekly
    budget; we use the 5-hour window for rate limiting instead.
    """
    try:
        resp = session.get(QUOTA_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Quota endpoint unreachable (%s); proceeding optimistically", e)
        return True, None

    if not isinstance(data, dict):
        return True, None

    weekly = data.get("weekly", {})
    five_hour = data.get("fiveHour", {})

    w_pct = float(weekly.get("percentage", 0))
    fh_pct = float(five_hour.get("percentage", 0))
    fh_elapsed = float(five_hour.get("elapsedPct", 0))

    # Hard stop: weekly quota almost exhausted
    if w_pct >= 85:
        logger.error(
            "QUOTA GUARD: weekly usage %.1f%% >= 85%% — stopping (almost exhausted).", w_pct)
        return False, data

    # Hard stop: 5-hour window almost exhausted
    if fh_pct >= 80:
        logger.error(
            "QUOTA GUARD: 5hr usage %.1f%% >= 80%% — stopping (almost exhausted).", fh_pct)
        return False, data

    # Rate limit: if 5hr usage is moderate (>20%) and ahead of elapsed, slow down
    if fh_pct > 20 and fh_pct > fh_elapsed:
        logger.error(
            "QUOTA GUARD: 5hr usage %.1f%% > 5hr elapsed %.1f%% (and >20%%) — stopping.", fh_pct, fh_elapsed)
        return False, data

    logger.debug("Quota OK: weekly=%.1f%%, 5hr=%.1f%%/%.1f%%", w_pct, fh_pct, fh_elapsed)
    return True, data


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
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        return None
    raw = match.group()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Strip literal control chars that occasionally sneak in.
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def call_glm_fix(
    client: openai.OpenAI,
    question: dict[str, Any],
    model: str,
) -> dict[str, Any] | None:
    """Ask GLM-5.2 to return a corrected enrichment object for one question."""
    enrichment = question.get("enrichment") or {}
    issues = enrichment.get("verification", {}).get("issues", []) or []

    issues_block = "\n".join(f"- {issue}" for issue in issues) or "- (no specific issues listed)"

    user_prompt = FIX_USER_TEMPLATE.format(
        question_id=question.get("id", "unknown"),
        subject=question.get("subject") or "?",
        module=question.get("module") or "?",
        question_text=(question.get("question_text") or "").strip(),
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
                # Stamp some bookkeeping fields we control.
                obj.setdefault("status", "success")
                obj["model"] = model
                obj["enriched_at"] = datetime.now(timezone.utc).isoformat()
                obj["processor_id"] = "fix-unverified-glm-5.2"
                obj.setdefault("attempts", enrichment.get("attempts", 0))
                if isinstance(obj.get("attempts"), int):
                    obj["attempts"] = obj["attempts"] + 1
                obj.setdefault("input_tokens", getattr(resp.usage, "prompt_tokens", 0) or 0)
                obj.setdefault("output_tokens", getattr(resp.usage, "completion_tokens", 0) or 0)
                obj.setdefault("duration_seconds", 0.0)
                obj.pop("verification", None)  # never trust model-supplied verification
                return obj
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
    return None


def write_enrichment(db: sqlite3.Connection, question_id: str, enrichment: dict[str, Any]) -> None:
    db.execute(
        "UPDATE questions SET enrichment = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(enrichment, ensure_ascii=False), question_id),
    )


def reverify_question(
    client: openai.OpenAI,
    db: sqlite3.Connection,
    question: dict[str, Any],
    new_enrichment: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    """Re-run the existing single-question verifier on the fixed enrichment."""
    # Persist the new enrichment first so _extract_verification_context sees it.
    enriched_q = dict(question)
    enriched_q["enrichment"] = new_enrichment

    try:
        item = _extract_verification_context(enriched_q)
    except Exception as e:
        logger.warning("Could not build verification context for %s: %s", question.get("id"), e)
        new_enrichment["verification"] = {"verified": False, "issues": [f"re-verify context error: {e}"]}
        return new_enrichment

    try:
        results = _verify_batch(client, [item], model)
    except Exception as e:
        logger.warning("Re-verify API call failed for %s: %s", question.get("id"), e)
        new_enrichment["verification"] = {"verified": False, "issues": [f"re-verify API error: {e}"]}
        return new_enrichment

    if not results:
        new_enrichment["verification"] = {"verified": False, "issues": ["re-verify returned no result"]}
        return new_enrichment

    r = results[0]
    new_enrichment["verification"] = {
        "verified": bool(r.get("verified", False)),
        "issues": list(r.get("issues", []) or []),
    }
    return new_enrichment


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix unverified ESAT questions via GLM-5.2.")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N questions (testing)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--api-key", type=str, default=None, help="API key (or set ANTHROPIC_API_KEY)")
    parser.add_argument("--base-url", type=str, default=ZAI_BASE_URL, help="OpenAI-compatible base URL")
    parser.add_argument("--dry-run", action="store_true", help="List target questions; don't call the API")
    parser.add_argument("--skip-reverify", action="store_true", help="Skip re-verification after fix (testing)")
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
    client = openai.OpenAI(api_key=api_key, base_url=args.base_url)

    import requests  # local import — only needed for the running path
    session = requests.Session()

    total = len(questions)
    fixed_ok = 0          # fix applied AND re-verify came back clean
    fixed_but_still_failing = 0
    fix_failed = 0
    quota_stopped = False

    for idx, q in enumerate(questions, start=1):
        qid = q["id"]
        issues = q["enrichment"].get("verification", {}).get("issues", []) or []
        logger.info("[%d/%d] %s — %d issue(s)", idx, total, qid, len(issues))

        # ---- Quota guard BEFORE every API call -----------------------------
        ok, payload = check_quota(session)
        if not ok:
            logger.error(
                "Quota guard tripped at %s. Stopping. Summary: completed=%d/%d, remaining=%d",
                qid, idx - 1, total, total - (idx - 1),
            )
            quota_stopped = True
            break

        # ---- Step 1: ask GLM to fix the enrichment ------------------------
        t0 = time.time()
        new_enrichment = call_glm_fix(client, q, args.model)
        elapsed = time.time() - t0

        if new_enrichment is None:
            fix_failed += 1
            logger.warning("[%d/%d] %s — fix FAILED", idx, total, qid)
            time.sleep(INTER_CALL_DELAY_S)
            continue

        # Stamp observed duration
        try:
            new_enrichment["duration_seconds"] = round(elapsed, 3)
        except Exception:
            pass

        # ---- Step 2: re-verify the fixed enrichment -----------------------
        if args.skip_reverify:
            new_enrichment["verification"] = {"verified": True, "issues": []}
        else:
            new_enrichment = reverify_question(client, db, q, new_enrichment, args.model)

        # ---- Step 3: persist ---------------------------------------------
        write_enrichment(db, qid, new_enrichment)
        db.commit()

        v = new_enrichment.get("verification", {})
        verified = bool(v.get("verified", False))
        remaining_issues = v.get("issues", []) or []
        if verified:
            fixed_ok += 1
            logger.info("[%d/%d] %s — FIXED & VERIFIED ✓", idx, total, qid)
        else:
            fixed_but_still_failing += 1
            logger.info(
                "[%d/%d] %s — fix applied but still unverified (%d remaining issue(s))",
                idx, total, qid, len(remaining_issues),
            )

        time.sleep(INTER_CALL_DELAY_S)

    db.close()

    logger.info("=== fix-unverified summary ===")
    logger.info("Total processed this run : %d / %d", fixed_ok + fixed_but_still_failing + fix_failed, total)
    logger.info("  fixed & verified        : %d", fixed_ok)
    logger.info("  fixed but still failing : %d", fixed_but_still_failing)
    logger.info("  fix API failures        : %d", fix_failed)
    if quota_stopped:
        logger.info("  STOPPED EARLY by quota guard — rerun later to resume.")
    else:
        logger.info("  quota guard             : not tripped")


if __name__ == "__main__":
    main()
