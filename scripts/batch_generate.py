#!/usr/bin/env python3
"""
Batch ESAT question generator — ESA-39 Part 1 / ESA-42 generate→verify loop.

Burns through Gemini free-tier keys generating questions across all
available spec topics × difficulties. After each question is generated,
the full quality stack (`scripts/quality/run_all.py`) runs immediately:
only questions that pass every applicable gate are inserted into the
website's questions database. Failed questions are recorded in
`generation_attempts` with status='rejected' and skipped (not retried).

Usage:
    python3 batch_generate.py                # run until both keys exhausted
    python3 batch_generate.py --max N        # stop after N questions
    python3 batch_generate.py --dry-run      # show plan, don't call API
    python3 batch_generate.py --skip-gates solver,reviewer   # bypass gates

Environment:
    GEMINI_API_KEY  — optional second key (Key 1). Key 2 is the hardcoded fallback.
"""

from __future__ import annotations

import json
import logging
import os
import random
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make sibling modules importable
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import generator as gen_mod

# Quality verification stack (ESA-42)
from quality import run_all as qa_run_all  # noqa: E402

logger = logging.getLogger("batch_generate")

# ──────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────

SHARED_DIR = SCRIPTS_DIR.parent
PATTERNS_DIR = SHARED_DIR / "patterns"
DB_PATH = SHARED_DIR / "data" / "questions.db"

DIFFICULTIES = ["Easy", "Medium", "Hard"]

# Two keys: env var (Key 1) + hardcoded fallback (Key 2).
KEY_ENV = os.environ.get("GEMINI_API_KEY")
KEY_FALLBACK = "AIzaSyBkiGJSS45VVKwZuTL6oXPl-K3_Qv9z-44"

# Build the active key list. Both keys get used in round-robin. If only
# one is available, we cycle through it alone (and stop on first exhaustion).
KEYS: list[str] = []
if KEY_ENV:
    KEYS.append(KEY_ENV)
KEYS.append(KEY_FALLBACK)

# Sleep between calls to be gentle with rate limits (seconds).
INTER_CALL_DELAY = 1.0
# On 429: sleep this long before trying next key (seconds).
RATE_LIMIT_SLEEP = 30.0
# Max consecutive 429s across all keys before we declare both exhausted.
MAX_GLOBAL_429 = len(KEYS) * 3


# ──────────────────────────────────────────────────────────────────────────
# Spec discovery
# ──────────────────────────────────────────────────────────────────────────


def discover_specs(patterns_dir: Path = PATTERNS_DIR) -> list[str]:
    """Return sorted list of spec codes that have complete pattern bundles."""
    specs: list[str] = []
    for d in sorted(patterns_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        children = [f.name for f in d.iterdir()]
        has_style = any(f.startswith("style_guide.") for f in children)
        has_distractor = any(f.startswith("distractor_catalogue.") for f in children)
        has_insight = any(f.startswith("insight_scenarios.") for f in children)
        if has_style and has_distractor and has_insight:
            specs.append(d.name)
    return specs


def build_work_queue(specs: list[str], difficulties: list[str]) -> list[tuple[str, str]]:
    """Cartesian product of specs × difficulties, shuffled for coverage diversity."""
    queue = [(s, d) for s in specs for d in difficulties]
    random.shuffle(queue)
    return queue


# ──────────────────────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────────────────────


def get_dbconn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist (mirrors src/lib/db.ts)."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS questions (
          id              TEXT PRIMARY KEY,
          exam_type       TEXT NOT NULL,
          year            TEXT,
          paper           TEXT,
          module          TEXT,
          section         TEXT,
          subject         TEXT,
          part            TEXT,
          question_number INTEGER NOT NULL,
          question_text   TEXT NOT NULL,
          question_images TEXT DEFAULT '[]',
          options         TEXT NOT NULL,
          correct_answer  TEXT NOT NULL,
          explanation     TEXT DEFAULT '',
          explanation_images TEXT DEFAULT '[]',
          screenshot      TEXT DEFAULT '',
          enrichment      TEXT,
          metadata        TEXT DEFAULT '{}',
          source          TEXT NOT NULL DEFAULT 'corpus',
          generated_from_template_id TEXT,
          difficulty_score REAL,
          created_at      TEXT DEFAULT (datetime('now')),
          updated_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_questions_exam_type ON questions(exam_type);
        CREATE INDEX IF NOT EXISTS idx_questions_year ON questions(year);
        CREATE INDEX IF NOT EXISTS idx_questions_module ON questions(module);
        CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject);
        CREATE INDEX IF NOT EXISTS idx_questions_source ON questions(source);

        CREATE TABLE IF NOT EXISTS attempt_stats (
          question_id     TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
          times_answered  INTEGER DEFAULT 0,
          times_correct   INTEGER DEFAULT 0,
          avg_time_ms     REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS generation_attempts (
          id              TEXT PRIMARY KEY,
          batch_id        TEXT NOT NULL,
          spec_topic      TEXT NOT NULL,
          model           TEXT NOT NULL,
          prompt_hash     TEXT,
          question_text   TEXT NOT NULL,
          options         TEXT NOT NULL,
          correct_answer  TEXT NOT NULL,
          explanation     TEXT DEFAULT '',
          status          TEXT NOT NULL DEFAULT 'pending',
          reject_reason   TEXT,
          question_id     TEXT,
          created_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_attempts_batch ON generation_attempts(batch_id);
        CREATE INDEX IF NOT EXISTS idx_attempts_topic ON generation_attempts(spec_topic);
        CREATE INDEX IF NOT EXISTS idx_attempts_status ON generation_attempts(status);
        CREATE INDEX IF NOT EXISTS idx_attempts_model ON generation_attempts(model);
        """
    )
    conn.commit()


def insert_question(
    conn: sqlite3.Connection,
    question: dict[str, Any],
    gen_result: gen_mod.GenResult,
    batch_id: str,
    verification_summary: dict[str, Any] | None = None,
) -> str:
    """Insert a generated question into both questions and generation_attempts.

    `verification_summary` (from `quality.run_all.run_all`) is folded into
    `metadata.verification` so the website and downstream tools can surface
    per-gate verdicts without re-running the stack.
    """
    qid = f"gen-{uuid.uuid4().hex[:12]}"
    attempt_id = f"att-{uuid.uuid4().hex[:12]}"

    now = datetime.now(timezone.utc).isoformat(sep=" ", timespec="seconds")
    module = question.get("module", "")
    spec_topic = question.get("spec_topic", "")
    options_json = json.dumps(question.get("options", {}))
    metadata = question.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    if verification_summary is not None:
        metadata = dict(metadata)
        metadata["verification"] = verification_summary
    metadata_json = json.dumps(metadata)

    # Insert into questions table
    conn.execute(
        """INSERT INTO questions (
            id, exam_type, year, paper, module, section, subject, part,
            question_number, question_text, question_images, options,
            correct_answer, explanation, explanation_images, screenshot,
            enrichment, metadata, source, generated_from_template_id,
            difficulty_score, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            qid,
            "esat",
            None,
            "ESAT",
            module,
            "",
            "",
            "",
            0,
            question["question_text"],
            "[]",
            options_json,
            question["correct_answer"],
            question.get("explanation", ""),
            "[]",
            "",
            None,
            metadata_json,
            "generated",
            question.get("generated_from_template_id"),
            None,
            now,
            now,
        ),
    )

    # Insert into generation_attempts
    conn.execute(
        """INSERT INTO generation_attempts (
            id, batch_id, spec_topic, model, prompt_hash,
            question_text, options, correct_answer, explanation,
            status, question_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            attempt_id,
            batch_id,
            spec_topic,
            gen_result.model,
            question.get("prompt_hash"),
            question["question_text"],
            options_json,
            question["correct_answer"],
            question.get("explanation", ""),
            "accepted",
            qid,
            now,
        ),
    )

    conn.commit()
    return qid


def record_rejected_attempt(
    conn: sqlite3.Connection,
    question: dict[str, Any],
    gen_result: gen_mod.GenResult,
    batch_id: str,
    verification_summary: dict[str, Any],
) -> str:
    """Record a rejected (failed verification) attempt in generation_attempts only.

    Per ESA-42: failed questions are logged and skipped, not retried. The
    question is NOT inserted into the `questions` table.
    """
    attempt_id = f"att-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat(sep=" ", timespec="seconds")
    spec_topic = question.get("spec_topic", "")
    options_json = json.dumps(question.get("options", {}))

    # Build a compact reject reason: which gates failed and why.
    failed_gates = []
    for key, info in verification_summary.get("gates", {}).items():
        if info.get("skipped"):
            continue
        if not info.get("pass"):
            failed_gates.append(
                f"{key}: {info.get('reason', 'no reason')}"
            )
    reject_reason = "; ".join(failed_gates) or "verification_failed"

    conn.execute(
        """INSERT INTO generation_attempts (
            id, batch_id, spec_topic, model, prompt_hash,
            question_text, options, correct_answer, explanation,
            status, reject_reason, question_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            attempt_id,
            batch_id,
            spec_topic,
            gen_result.model,
            question.get("prompt_hash"),
            question["question_text"],
            options_json,
            question["correct_answer"],
            question.get("explanation", ""),
            "rejected",
            reject_reason[:500],  # bound the size
            None,
            now,
        ),
    )
    conn.commit()
    return attempt_id


def verify_question(
    question: dict[str, Any],
    *,
    skip_gates: set[str] | None = None,
) -> dict[str, Any]:
    """Run the full quality stack against a freshly generated question.

    Returns the summary dict from `quality.run_all.run_all`. The caller
    decides accept/reject based on `summary["pass"]`.
    """
    return qa_run_all.run_all(question, skip=skip_gates)


def verify_and_store(
    conn: sqlite3.Connection,
    question: dict[str, Any],
    gen_result: gen_mod.GenResult,
    batch_id: str,
    *,
    skip_gates: set[str] | None = None,
) -> tuple[str | None, dict[str, Any], bool]:
    """Run the verification gates and route the question.

    Returns (qid_or_none, verification_summary, accepted). On accept, the
    question is inserted into both `questions` and `generation_attempts`
    (status='accepted'). On reject, only `generation_attempts` is written
    with status='rejected' and `reject_reason` populated — the question
    is not retried.
    """
    summary = verify_question(question, skip_gates=skip_gates)
    if summary.get("pass"):
        qid = insert_question(conn, question, gen_result, batch_id, summary)
        return qid, summary, True
    record_rejected_attempt(conn, question, gen_result, batch_id, summary)
    return None, summary, False


def count_generated(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM questions WHERE source = 'generated'").fetchone()
    return row[0] if row else 0


# ──────────────────────────────────────────────────────────────────────────
# Key rotation
# ──────────────────────────────────────────────────────────────────────────


class KeyManager:
    """Round-robin key rotation with exhaustion tracking."""

    def __init__(self, keys: list[str]):
        self.keys = list(keys)
        self.idx = 0
        self.exhausted: set[int] = set()
        self.call_counts: dict[int, int] = {i: 0 for i in range(len(keys))}

    def next_key(self) -> str | None:
        """Return the next non-exhausted key, or None if all exhausted."""
        if len(self.exhausted) >= len(self.keys):
            return None
        # Find next non-exhausted key starting from current idx
        for _ in range(len(self.keys)):
            if self.idx not in self.exhausted:
                key = self.keys[self.idx]
                self.call_counts[self.idx] += 1
                self.idx = (self.idx + 1) % len(self.keys)
                return key
            self.idx = (self.idx + 1) % len(self.keys)
        return None

    def mark_exhausted(self) -> None:
        """Mark the key that was just used as exhausted."""
        # Mark the previous key (the one before we advanced)
        prev = (self.idx - 1) % len(self.keys)
        self.exhausted.add(prev)
        logger.warning(
            "Key #%d marked exhausted (%d/%d keys remaining)",
            prev,
            len(self.keys) - len(self.exhausted),
            len(self.keys),
        )

    def all_exhausted(self) -> bool:
        return len(self.exhausted) >= len(self.keys)

    def stats(self) -> str:
        parts = []
        for i, k in enumerate(self.keys):
            status = "EXHAUSTED" if i in self.exhausted else "active"
            masked = k[:8] + "..." if k else "None"
            parts.append(f"key{i}({masked}, {status}, calls={self.call_counts[i]})")
        return ", ".join(parts)


# ──────────────────────────────────────────────────────────────────────────
# Generation with key rotation
# ──────────────────────────────────────────────────────────────────────────


def generate_with_key(
    spec_code: str,
    difficulty: str,
    api_key: str,
    seed: int | None = None,
) -> tuple[dict[str, Any], gen_mod.GenResult]:
    """Generate one question using a specific API key."""
    # Temporarily set the module-level key so _call_gemini picks it up
    original = gen_mod.PRIMARY_API_KEY
    gen_mod.PRIMARY_API_KEY = api_key
    try:
        return gen_mod.generate(spec_code, difficulty, seed=seed)
    finally:
        gen_mod.PRIMARY_API_KEY = original


def run_batch(
    *,
    max_questions: int | None = None,
    dry_run: bool = False,
    skip_gates: set[str] | None = None,
) -> int:
    """Main batch loop. Returns total questions accepted this run.

    ESA-42: every generated question runs through the quality stack
    (`scripts/quality/run_all.py`) immediately. Only questions that pass
    every applicable gate are inserted into the `questions` table. Failed
    questions are recorded in `generation_attempts` with status='rejected'
    and skipped (not retried).
    """

    specs = discover_specs()
    if not specs:
        logger.error("No complete pattern bundles found in %s", PATTERNS_DIR)
        return 1

    queue = build_work_queue(specs, DIFFICULTIES)
    logger.info(
        "Discovered %d spec codes × %d difficulties = %d (spec, diff) combos",
        len(specs), len(DIFFICULTIES), len(queue),
    )
    logger.info("Active keys: %d (%s)", len(KEYS), "env+fallback" if len(KEYS) > 1 else "fallback only")
    if skip_gates:
        logger.warning("SKIP GATES: %s (verification will be bypassed for these)", ",".join(sorted(skip_gates)))

    if dry_run:
        print(f"\nDry run — {len(queue)} combos ready:")
        for spec, diff in queue[:10]:
            print(f"  {spec} / {diff}")
        print(f"  ... ({len(queue)} total)")
        return 0

    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_dbconn()
    init_db_schema(conn)

    existing = count_generated(conn)
    logger.info("Database: %s (existing generated questions: %d)", DB_PATH, existing)

    kmgr = KeyManager(KEYS)
    batch_id = f"batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    accepted_this_run = 0
    rejected_this_run = 0
    total_new = existing
    consecutive_429 = 0
    errors = 0
    total_input_tokens = 0
    total_output_tokens = 0
    queue_idx = 0

    logger.info("Starting batch %s (generate→verify loop)", batch_id)

    def process_one(spec_code: str, difficulty: str, key: str) -> tuple[bool, bool]:
        """Generate → verify → store one question.

        Returns (accepted, rate_limited). `accepted` is True if the
        question passed verification and was inserted into `questions`.
        `rate_limited` is True if the API key hit a 429/quota error.
        """
        nonlocal accepted_this_run, rejected_this_run, total_new
        nonlocal total_input_tokens, total_output_tokens, consecutive_429

        seed = random.randint(1, 2**31)
        question, gen_result = generate_with_key(spec_code, difficulty, key, seed=seed)
        consecutive_429 = 0  # reset on successful generation
        total_input_tokens += gen_result.input_tokens
        total_output_tokens += gen_result.output_tokens

        # ESA-42: immediate verification gate. No retries on reject.
        try:
            qid, summary, accepted = verify_and_store(
                conn, question, gen_result, batch_id, skip_gates=skip_gates,
            )
        except Exception as exc:
            # Verification stack crashed — record as rejected so we don't
            # silently drop the question, but keep the batch moving.
            logger.error(
                "Verification crashed for %s/%s: %s: %s — recording as rejected",
                spec_code, difficulty, type(exc).__name__, exc,
            )
            record_rejected_attempt(
                conn, question, gen_result, batch_id,
                {"pass": False, "gates": {}, "total_cost_usd": 0.0,
                 "within_budget": True, "budget_usd": qa_run_all.COST_BUDGET_USD},
            )
            rejected_this_run += 1
            return False, False

        if accepted:
            accepted_this_run += 1
            total_new += 1
            cost = summary.get("total_cost_usd", 0.0)
            if accepted_this_run % 10 == 0 or accepted_this_run <= 5:
                logger.info(
                    "[accept %d] %s / %s → %s (model=%s, tokens=%d+%d, qa_cost=$%.5f) | total=%d | %s",
                    accepted_this_run, spec_code, difficulty, qid,
                    gen_result.model, gen_result.input_tokens, gen_result.output_tokens,
                    cost, total_new, kmgr.stats(),
                )
        else:
            rejected_this_run += 1
            failed = [
                k for k, v in summary.get("gates", {}).items()
                if not v.get("skipped") and not v.get("pass")
            ]
            logger.warning(
                "[reject %d] %s / %s — failed gates: %s | %s",
                rejected_this_run, spec_code, difficulty,
                ",".join(failed) or "unknown",
                question.get("correct_answer", "?"),
            )
        return accepted, False

    # ── First pass: every (spec, difficulty) once ────────────────────────
    while queue_idx < len(queue):
        if max_questions is not None and accepted_this_run >= max_questions:
            logger.info("Reached --max=%d accepted, stopping", max_questions)
            break

        if kmgr.all_exhausted():
            logger.warning("All API keys exhausted — stopping.")
            break

        spec_code, difficulty = queue[queue_idx]
        queue_idx += 1

        key = kmgr.next_key()
        if key is None:
            logger.warning("No available keys — stopping.")
            break

        try:
            process_one(spec_code, difficulty, key)
        except RuntimeError as exc:
            exc_str = str(exc).lower()
            if "429" in exc_str or "quota" in exc_str or "rate" in exc_str or "resource_exhausted" in exc_str:
                consecutive_429 += 1
                logger.warning(
                    "Rate limit on key for %s/%s (consecutive=%d)",
                    spec_code, difficulty, consecutive_429,
                )
                kmgr.mark_exhausted()

                if consecutive_429 >= MAX_GLOBAL_429:
                    logger.error("Hit %d consecutive rate limits — all keys likely exhausted.", MAX_GLOBAL_429)
                    break

                logger.info("Sleeping %.0fs before next attempt...", RATE_LIMIT_SLEEP)
                time.sleep(RATE_LIMIT_SLEEP)
                # Don't advance queue for this combo — retry with next key
                queue_idx -= 1
            else:
                errors += 1
                logger.error(
                    "Generation failed for %s/%s: %s", spec_code, difficulty, exc,
                )
                if errors > 20:
                    logger.error("Too many errors (>20) — stopping.")
                    break
        except Exception as exc:
            errors += 1
            logger.error(
                "Unexpected error for %s/%s: %s: %s",
                spec_code, difficulty, type(exc).__name__, exc,
            )
            if errors > 20:
                logger.error("Too many errors (>20) — stopping.")
                break

        # Gentle delay between calls
        time.sleep(INTER_CALL_DELAY)

    # ── Second pass: keep drawing random combos until quota exhausted ────
    if queue_idx >= len(queue) and not kmgr.all_exhausted() and (max_questions is None or accepted_this_run < max_questions):
        logger.info("Completed full queue pass — reshuffling and continuing for more coverage...")
        while not kmgr.all_exhausted() and (max_questions is None or accepted_this_run < max_questions):
            spec_code = random.choice(specs)
            difficulty = random.choice(DIFFICULTIES)
            key = kmgr.next_key()
            if key is None:
                break

            try:
                process_one(spec_code, difficulty, key)
            except RuntimeError as exc:
                exc_str = str(exc).lower()
                if "429" in exc_str or "quota" in exc_str or "rate" in exc_str or "resource_exhausted" in exc_str:
                    kmgr.mark_exhausted()
                    if kmgr.all_exhausted():
                        logger.warning("All keys exhausted — done.")
                        break
                    logger.info("Sleeping %.0fs...", RATE_LIMIT_SLEEP)
                    time.sleep(RATE_LIMIT_SLEEP)
                else:
                    errors += 1
                    logger.error("Generation failed for %s/%s: %s", spec_code, difficulty, exc)
            except Exception as exc:
                errors += 1
                logger.error("Unexpected error: %s: %s", type(exc).__name__, exc)

            time.sleep(INTER_CALL_DELAY)

    conn.close()

    attempted = accepted_this_run + rejected_this_run
    accept_rate = (accepted_this_run / attempted * 100.0) if attempted else 0.0

    # Summary
    logger.info("=" * 60)
    logger.info("BATCH COMPLETE: %s", batch_id)
    logger.info("  Attempted (generated): %d", attempted)
    logger.info("  Accepted (passed verification): %d (%.1f%%)", accepted_this_run, accept_rate)
    logger.info("  Rejected (failed verification): %d", rejected_this_run)
    logger.info("  Total generated in DB: %d", total_new)
    logger.info("  Errors: %d", errors)
    logger.info("  Total tokens: %d input + %d output", total_input_tokens, total_output_tokens)
    logger.info("  Key stats: %s", kmgr.stats())
    logger.info("=" * 60)

    return accepted_this_run


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Batch ESAT question generator (generate→verify)")
    p.add_argument("--max", type=int, default=None, help="Max questions to accept (passed verification)")
    p.add_argument("--dry-run", action="store_true", help="Show plan without calling API")
    p.add_argument(
        "--skip-gates",
        default="",
        help="Comma-separated gate keys to skip (calculator,sympy,solver,reviewer,chem_stoich,bio_judge)",
    )
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    skip_gates = {s.strip() for s in args.skip_gates.split(",") if s.strip()}
    count = run_batch(max_questions=args.max, dry_run=args.dry_run, skip_gates=skip_gates or None)
    if isinstance(count, int) and count >= 0:
        print(f"\nDone. {count} questions accepted (passed verification).")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
