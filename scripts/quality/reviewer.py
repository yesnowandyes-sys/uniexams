#!/usr/bin/env python3
"""
LLM Reviewer Gate (Gate 4 of the 4-gate stack).

A Haiku-powered rubric judge scores four blocking 1-5 dimensions and one
advisory dimension: clarity, syllabus match, distractor plausibility, and
uniqueness (blocking/advisory as noted below), plus an advisory difficulty
assessment.

`clarity`, `syllabus`, and `distractors` are **blocking** (default ≥ 4 to
pass). `uniqueness` is **advisory only** — it is recorded in `scores` and
surfaced via the `advisory` field when low, but does not gate the question.

Rationale (ESA-37): the ESAT practice bank deliberately produces
template-derived, standard textbook-style questions. The LLM uniqueness
rubric is poorly calibrated for "is this a duplicate?" because it cannot
see the corpus, and its definition of "standard textbook-style" overlaps
with the product's target content. Actual near-duplicate detection is
handled by `scripts/dedup.py` (embedding similarity + shingle Jaccard +
concept cap), which compares against the real corpus.

Cost target: ~$0.00125 / question (ESA-22 acceptance criteria).

Standard verdict dict:

    {
        "pass": bool,
        "score": float,          # mean of blocking rubric dims in [0,1]
        "reason": str,
        "issues": list[str],     # blocking dimensions scoring < threshold
        "advisory": list[str],   # non-blocking observations (e.g. low uniqueness)
        "cost_usd": float,
        "scores": {"clarity": int, "syllabus": int, "distractors": int,
                   "uniqueness": int, "difficulty": int},
        "difficulty_score_llm": int,    # advisory 1-5, mirrors scores["difficulty"]
        "difficulty_band_llm": str,     # easy|medium|hard|very_hard
    }
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
    from _llm import call_haiku, DEFAULT_MODEL  # type: ignore
else:
    from .verdict import verdict  # type: ignore
    from ._llm import call_haiku, DEFAULT_MODEL  # type: ignore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reviewer prompt
# ---------------------------------------------------------------------------

REVIEWER_SYSTEM_PROMPT = """\
You are a senior ESAT examiner reviewing a draft question for the ESAT \
practice question bank. Score each of the four rubric dimensions 1–5, \
where 1 is unacceptable and 5 is exemplary.

Use the following rubric:

CLARITY:
  5 — Wording is unambiguous; all necessary information is present.
  4 — Minor wording could be tightened but solvable as written.
  3 — Some ambiguity; a careful student might still solve it.
  2 — Material ambiguity that affects solvability.
  1 — Unsolvable or self-contradictory as written.

SYLLABUS (match to ESAT Content Specification):
  5 — Plainly within syllabus for the stated module.
  4 — Within syllabus, borderline topic but reasonable.
  3 — Borderline; could be argued either way.
  2 — Likely out of syllabus or off-spec (e.g. g=9.81).
  1 — Clearly out of syllabus.

DISTRACTORS (plausibility of wrong options):
  5 — Every distractor corresponds to an identifiable student error.
  4 — All distractors plausible; one could be tighter.
  3 — One weak or absurd distractor.
  2 — Multiple weak distractors; right answer is obvious by elimination.
  1 — Distractors are obviously wrong / absurd values.

UNIQUENESS (advisory signal only — does NOT gate the question):
  5 — Novel context or twist; tests reasoning, not recall.
  4 — Standard topic but presented cleanly with a small twist.
  3 — Standard textbook-style question (expected median for practice bank).
  2 — Heavily templated; near-duplicate of common practice material.
  1 — Identical a well-known past paper question.
  Note: an embedding/shingle dedup pass against the existing corpus runs
  separately (scripts/dedup.py) and is the authoritative duplicate guard.

DIFFICULTY (advisory only — does NOT gate the question):
  5 — Very Hard: requires multi-step reasoning, concept synthesis, or
      non-obvious insight. Top ~10% of ESAT questions.
  4 — Hard: multiple concepts, non-trivial arithmetic, requires careful work.
      Typical hard ESAT questions.
  3 — Medium: straightforward application of one concept with moderate
      calculation. Standard ESAT difficulty.
  2 — Easy: simple single-step recall or basic arithmetic. Accessible to
      most candidates.
  1 — Trivial: basic recall with minimal calculation. Below typical ESAT
      level.

Output your review as FIVE lines in EXACTLY this format, in this order:

CLARITY: <int 1-5>
SYLLABUS: <int 1-5>
DISTRACTORS: <int 1-5>
UNIQUENESS: <int 1-5>
DIFFICULTY: <int 1-5>

Do not output anything else. No prose. No commentary. Just the five lines.
"""


def _format_options(options: Any) -> str:
    if isinstance(options, dict):
        return "\n".join(f"  {k}. {v}" for k, v in options.items())
    if isinstance(options, list):
        letters = "ABCDEFGHIABCDE"
        return "\n".join(f"  {letters[i]}. {v}" for i, v in enumerate(options))
    return str(options)


def _build_user_prompt(question: dict[str, Any]) -> str:
    options_str = _format_options(question.get("options"))
    correct = question.get("correct_answer", "unknown")
    solution = question.get("worked_solution") or question.get("explanation") or ""
    return (
        f"Module: {question.get('module', 'unknown')}\n"
        f"Topic: {question.get('topic', 'unknown')}\n"
        f"Stated correct answer: {correct}\n\n"
        f"Question:\n{question.get('question_text', '').strip()}\n\n"
        f"Options:\n{options_str}\n\n"
        f"Worked solution:\n{solution.strip()}\n"
    )


DIMENSION_KEYS = ("clarity", "syllabus", "distractors", "uniqueness", "difficulty")
BLOCKING_DIMS = ("clarity", "syllabus", "distractors")
# `difficulty` is recorded in `scores` and surfaced via `difficulty_score_llm`
# / `difficulty_band_llm` on the verdict. It never gates since it's absent
# from BLOCKING_DIMS. The uniqueness-floor warning below is uniqueness-
# specific (its message references dedup.py) and does not apply to it.
ADVISORY_DIMS = ("uniqueness", "difficulty")
DIMENSION_PATTERNS = {
    "clarity": re.compile(r"CLARITY:\s*(\d+)", re.IGNORECASE),
    "syllabus": re.compile(r"SYLLABUS:\s*(\d+)", re.IGNORECASE),
    "distractors": re.compile(r"DISTRACTORS:\s*(\d+)", re.IGNORECASE),
    "uniqueness": re.compile(r"UNIQUENESS:\s*(\d+)", re.IGNORECASE),
    "difficulty": re.compile(r"DIFFICULTY:\s*(\d+)", re.IGNORECASE),
}


def _parse_scores(text: str) -> dict[str, int] | None:
    scores: dict[str, int] = {}
    for key, pattern in DIMENSION_PATTERNS.items():
        m = pattern.search(text)
        if not m:
            return None
        val = int(m.group(1))
        if not 1 <= val <= 5:
            return None
        scores[key] = val
    return scores


# ---------------------------------------------------------------------------
# Core gate
# ---------------------------------------------------------------------------

ACCEPT_THRESHOLD = 4  # ESA-22 acceptance: each blocking dim ≥ 4
# Floor below which the advisory uniqueness score is surfaced as a warning.
# Default is 2 (heavily templated / near-duplicate of common material) —
# the dedup pipeline handles actual corpus duplicates.
UNIQUENESS_ADVISORY_FLOOR = 2

# Maps the advisory LLM difficulty score to the same band labels used by
# scripts/quality/structural_difficulty.py.
DIFFICULTY_BAND_MAP = {
    1: "easy",
    2: "easy",
    3: "medium",
    4: "hard",
    5: "very_hard",
}


def check(
    question: dict[str, Any],
    *,
    model: str | None = None,
    threshold: int = ACCEPT_THRESHOLD,
    uniqueness_floor: int = UNIQUENESS_ADVISORY_FLOOR,
    blocking_dims: tuple[str, ...] = BLOCKING_DIMS,
) -> dict[str, Any]:
    """Run the Haiku rubric over the question.

    Pass iff every dim in `blocking_dims` scores ≥ `threshold`. Dimensions
    in `ADVISORY_DIMS` (`uniqueness`, `difficulty`) are recorded but never
    gate the verdict. `uniqueness` appears in `advisory` when below
    `uniqueness_floor`; `difficulty` is surfaced via `difficulty_score_llm`
    / `difficulty_band_llm`.
    """
    try:
        result = call_haiku(
            user_prompt=_build_user_prompt(question),
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            model=model or DEFAULT_MODEL,
            max_tokens=1024,
            temperature=0.0,
        )
    except Exception as exc:
        logger.error("reviewer Haiku call failed: %s", exc)
        return verdict(
            passed=False,
            score=0.0,
            reason=f"reviewer API call failed: {exc}",
            issues=[str(exc)],
            cost_usd=0.0,
            gate="reviewer",
            scores={},
        )

    scores = _parse_scores(result.text)
    if scores is None:
        return verdict(
            passed=False,
            score=0.0,
            reason="reviewer returned unparseable scores",
            issues=[f"raw: {result.text[:300]!r}"],
            cost_usd=result.cost_usd,
            gate="reviewer",
            scores={},
        )

    failed_dims = [k for k in blocking_dims if scores.get(k, 0) < threshold]
    # Mean over blocking dims only — advisory dims don't pull the score.
    mean_rubric = (
        sum(scores[k] for k in blocking_dims)
        / (5 * len(blocking_dims))
    )
    passed = not failed_dims

    advisory: list[str] = []
    if "uniqueness" not in blocking_dims and scores.get("uniqueness", 5) < uniqueness_floor:
        advisory.append(
            f"uniqueness={scores['uniqueness']} "
            f"(<{uniqueness_floor} floor; rely on dedup.py)"
        )

    difficulty_score_llm = scores.get("difficulty")
    difficulty_band_llm = DIFFICULTY_BAND_MAP.get(difficulty_score_llm)

    reason = (
        f"all blocking dims ≥ {threshold}"
        if passed
        else f"dims below {threshold}: {', '.join(failed_dims)}"
    )
    if advisory and passed:
        reason += "; advisory: " + "; ".join(advisory)

    return verdict(
        passed=passed,
        score=round(mean_rubric, 3),
        reason=reason,
        issues=[
            f"{k}={scores[k]} (<{threshold})" for k in failed_dims
        ],
        advisory=advisory,
        cost_usd=result.cost_usd,
        gate="reviewer",
        scores=scores,
        model=result.model,
        difficulty_score_llm=difficulty_score_llm,
        difficulty_band_llm=difficulty_band_llm,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_question(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data:
        return data["questions"][0]
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT reviewer gate")
    p.add_argument("--question", type=Path, help="Path to a question JSON file")
    p.add_argument("--model", default=None)
    p.add_argument("--threshold", type=int, default=ACCEPT_THRESHOLD)
    p.add_argument(
        "--uniqueness-floor",
        type=int,
        default=UNIQUENESS_ADVISORY_FLOOR,
        help="Advisory floor for uniqueness (does not block; default 2)",
    )
    args = p.parse_args(argv)

    if not args.question:
        p.error("--question is required")
    question = _load_question(args.question)
    result = check(
        question,
        model=args.model,
        threshold=args.threshold,
        uniqueness_floor=args.uniqueness_floor,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
