#!/usr/bin/env python3
"""
Corpus few-shot exemplar fetcher for the ESAT generators (ESA-45, Part A).

Before every generation call the generator pulls **4 real past-paper
questions** from the enriched corpus that match the target topic AND
difficulty, and injects them into the prompt as few-shot exemplars. Each
exemplar carries:

* the question text,
* the A–E options,
* the marked correct answer, and
* the worked solution (the enrichment `markdown` field).

Matching rules (per Gilbert, non-negotiable):

* Match on the **topic_code** (section-level: the part of the enrichment
  `topic_classification.topic_code` before the first dot) and the
  **difficulty_category**.
* Select **4** exemplars at random from the matches.
* If fewer than 4 exist at that exact topic + difficulty, use however many
  exist (minimum 1).
* **Never fall back to a different difficulty** — a cell with zero matches
  yields zero exemplars (generation proceeds without them).

Topic bridging: the generator works off a pattern-dir *spec_code*
(`BIO.B3`, `MATHS1.M5`, `PHYS.P2`, `CHEM.C10`, `MATHS2.MM2`). The corpus
enrichment stores a finer `topic_code` (`B3.1`, `M5.18`, `P2.2`, ...).
We bridge them by comparing the spec topic part (`B3`) to the section of
the enrichment topic_code (`B3.1` → `B3`). Section codes are unique across
modules (M1–7, MM1–8, P1–7, C1–16, B1–11), so this never collides.

Usage:
    from exemplars import fetch_exemplars, render_exemplars_block
    exs = fetch_exemplars("PHYS.P2", "Hard", db_path=DB_PATH, seed=seed)
    block = render_exemplars_block(exs)
"""

from __future__ import annotations

import json
import logging
import random
import sqlite3
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

SHARED_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = SHARED_DIR / "data" / "questions.db"

DEFAULT_N = 4            # spec: 4 few-shot exemplars per generation call
MIN_N = 1               # spec: minimum 1 when the cell is non-empty

# Canonical generation buckets (generator.VALID_DIFFICULTIES).
_CANONICAL = ("Easy", "Medium", "Hard")


def normalize_difficulty(raw: Any) -> Optional[str]:
    """Map a corpus `difficulty_category` string onto {Easy, Medium, Hard}.

    The enriched corpus uses mostly clean labels (Easy/Medium/Hard) but also
    carries noisy variants ("Moderate", "Standard application", "Medium-Hard",
    "Very Hard", …). These are folded onto the three canonical generation
    buckets. Unmappable / missing values return None and are skipped.
    """
    s = str(raw or "").strip().lower()
    if not s:
        return None
    if "very hard" in s:
        return "Hard"
    if "hard" in s:
        return "Hard"
    if "easy" in s or "straightforward" in s or s.startswith("low"):
        return "Easy"
    if any(k in s for k in ("medium", "moderate", "standard", "application",
                            "intermediate")):
        return "Medium"
    return None


def spec_topic_part(spec_code: str) -> str:
    """`PHYS.P2` → `P2`, `MATHS2.MM2` → `MM2`, `CHEM.C10` → `C10`."""
    return spec_code.split(".", 1)[1] if "." in spec_code else spec_code


def topic_section(topic_code: Any) -> str:
    """`B3.1` → `B3`, `M5.18` → `M5`, `P2` → `P2`."""
    return str(topic_code or "").split(".", 1)[0].strip().upper()


def fetch_exemplars(
    spec_code: str,
    difficulty: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
    n: int = DEFAULT_N,
    seed: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Return up to `n` real corpus exemplars for (spec_code, difficulty).

    Matches the corpus on the topic_code section AND the difficulty bucket.
    No difficulty fallback: an empty cell returns ``[]``. Selection is
    reproducible when `seed` is provided (matches the generator's seed).
    """
    diff = difficulty.strip().capitalize() if difficulty else ""
    if diff not in _CANONICAL:
        logger.warning("exemplar difficulty %r not in %s — returning no exemplars",
                       difficulty, _CANONICAL)
        return []

    want_topic = spec_topic_part(spec_code).upper()
    if not want_topic:
        return []

    if not Path(db_path).exists():
        logger.warning("exemplar DB not found at %s — no exemplars", db_path)
        return []

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """SELECT question_text, options, correct_answer, explanation, enrichment
               FROM questions
               WHERE enrichment IS NOT NULL AND enrichment != ''"""
        ).fetchall()
    finally:
        con.close()

    matches: list[dict[str, Any]] = []
    for r in rows:
        try:
            en = json.loads(r["enrichment"]) if r["enrichment"] else {}
        except (json.JSONDecodeError, TypeError):
            continue
        tc = en.get("topic_classification") or {}
        if tc.get("is_out_of_spec"):
            continue  # spec: exclude out-of-spec questions
        if topic_section(tc.get("topic_code")) != want_topic:
            continue
        if normalize_difficulty(en.get("difficulty_category")) != diff:
            continue  # exact difficulty — NO fallback

        options = r["options"]
        try:
            options = json.loads(options) if isinstance(options, str) else options
        except (json.JSONDecodeError, TypeError):
            options = options if isinstance(options, dict) else {}

        worked = en.get("markdown") or r["explanation"] or ""
        qt = (r["question_text"] or "").strip()
        if not qt:
            continue
        matches.append({
            "question_text": qt,
            "options": options if isinstance(options, dict) else {},
            "correct_answer": str(r["correct_answer"] or "").strip().upper(),
            "worked_solution": str(worked).strip(),
        })

    if not matches:
        logger.info("no corpus exemplars for %s @ %s (topic section %s) — "
                    "proceeding without exemplars", spec_code, diff, want_topic)
        return []

    take = max(MIN_N, min(n, len(matches)))
    rng = random.Random(seed)
    # sort first for deterministic ordering before sampling, then shuffle
    matches.sort(key=lambda d: d["question_text"])
    return rng.sample(matches, take)


def render_exemplars_block(exemplars: list[dict[str, Any]]) -> str:
    """Format exemplars as a few-shot block for the generation prompt.

    Exemplars are presented as *solved past-paper questions* the author should
    study for style/calibre — they are NOT to be copied. Returns "" when there
    are none.
    """
    if not exemplars:
        return ""

    def _fmt_options(opts: dict[str, Any]) -> str:
        if not isinstance(opts, dict) or not opts:
            return "  (no options recorded)"
        return "\n".join(f"  {k}. {v}" for k, v in opts.items())

    blocks: list[str] = []
    for i, ex in enumerate(exemplars, start=1):
        ca = ex.get("correct_answer", "?")
        opts = ex.get("options", {})
        answer_text = opts.get(ca, "") if isinstance(opts, dict) else ""
        answer_line = f"Correct answer: {ca}"
        if answer_text:
            answer_line += f" — {answer_text}"
        worked = (ex.get("worked_solution") or "").strip()
        if len(worked) > 900:
            worked = worked[:900].rstrip() + "…"
        blocks.append(
            f"### Exemplar {i}\n"
            f"Question: {ex.get('question_text', '').strip()}\n"
            f"Options:\n{_fmt_options(opts)}\n"
            f"{answer_line}\n"
            f"Worked solution:\n{worked}"
        )

    header = (
        f"## REAL PAST-PAPER EXEMPLARS ({len(exemplars)})\n"
        f"Study these for ESAT style, calibre, and calculator-free arithmetic. "
        f"Do NOT copy them — write an ORIGINAL question at the target difficulty. "
        f"Use them to calibrate number choice and option design."
    )
    return header + "\n\n" + "\n\n".join(blocks)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Fetch corpus exemplars for a spec/difficulty")
    p.add_argument("spec_code", help="e.g. PHYS.P2, BIO.B3, MATHS1.M5")
    p.add_argument("difficulty", choices=list(_CANONICAL))
    p.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    exs = fetch_exemplars(args.spec_code, args.difficulty,
                          db_path=args.db, seed=args.seed)
    print(f"# {len(exs)} exemplar(s) for {args.spec_code} @ {args.difficulty}\n")
    print(render_exemplars_block(exs))
