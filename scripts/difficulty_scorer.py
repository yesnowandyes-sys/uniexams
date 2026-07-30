#!/usr/bin/env python3
"""
Structural difficulty scorer for ESAT questions — ESA-17 §2.4 + §4 item 8.

NOT an LLM self-assessment. Scores difficulty from structural features of
the question + worked solution:

- Number of distinct solution steps (counted from the explanation)
- Multi-stage arithmetic (each numeric operation in the worked solution)
- Algebraic complexity (presence of simultaneous equations, quadratics,
  compound fractions, vector decomposition)
- Reading complexity (stem length, number of clauses, presence of
  multi-statement I/II/III options)

Returns a 0..1 score plus a band (Easy / Medium / Hard / Very Hard). The
caller (nightly orchestrator) enforces the 20/50/30 easy/medium/hard
target split by pulling the most under-represented band — this module
only *scores*; it does not enforce the distribution.

Usage:
    python3 difficulty_scorer.py --question path/to/q.json
    python3 difficulty_scorer.py --question q.json --label human-easy

Reference: ESA-17 plan §4.5, strategy §2.4 + §4 item 8,
`orchestration-review.md` Priority #4.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ──────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────

VALID_BANDS = ("Easy", "Medium", "Hard", "Very Hard")

# Strategy §3.2 target distribution (informational — the orchestrator
# enforces it, this module just reports the band).
TARGET_DISTRIBUTION = {"Easy": 0.20, "Medium": 0.50, "Hard": 0.30, "Very Hard": 0.00}

# Score → band mapping. Tuned so:
#   - 1-step integer arithmetic → Easy
#   - 2–3 step standard problem → Medium
#   - Multi-stage / algebraic / compound → Hard
#   - Multi-constraint + abstract reasoning → Very Hard
SCORE_BANDS = (
    (0.30, "Easy"),
    (0.55, "Medium"),
    (0.78, "Hard"),
    (1.01, "Very Hard"),
)


# ──────────────────────────────────────────────────────────────────────────
# Feature extraction
# ──────────────────────────────────────────────────────────────────────────


@dataclass
class Features:
    """Structural features extracted from a question."""

    stem_chars: int = 0
    stem_clauses: int = 0           # count of sentence-like clauses in the stem
    option_count: int = 0
    multi_statement_options: bool = False  # I/II/III/IV style options
    solution_steps: int = 0         # numbered/bulleted steps in explanation
    arithmetic_ops: int = 0         # ×, ÷, +, −, ^ in worked solution
    has_quadratic: bool = False
    has_simultaneous: bool = False
    has_compound_fraction: bool = False
    has_vector_decomp: bool = False
    has_log_exp: bool = False
    has_trig: bool = False
    has_calculus: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


_CLAUSE_SPLIT = re.compile(r"[.;]\s+")
_ROMAN_OPTION = re.compile(r"\b[IVX]{1,4}\b")
# Step detection — supports three explanation styles:
#   (a) explicit markers: "1.", "2)", "-", "*", "•", "Step N:"
#   (b) blank-line separated blocks (each equation/paragraph = a step)
#   (c) sentence-separated steps within a single paragraph
_STEP_MARKERS = re.compile(r"(?:^|\n)\s*(?:\d+[.)]|[-*•]|Step\s+\d+[:.])\s+", re.IGNORECASE)
_STEP_SENTENCE = re.compile(r"[.!?]\s+(?=[A-Z$\\])")
_ARITH = re.compile(r"[×÷+\-^]|\\(?:times|div|frac|sqrt)")
_QUADRATIC = re.compile(r"x\^2|x²|\\sqrt|ax\^2 \+ bx")
_SIMULTANEOUS = re.compile(r"simultaneous|solve(?:\s+for)?\s+both|two\s+equations")
_COMPOUND_FRAC = re.compile(r"\\frac\{[^}]*\\frac")
_VECTOR = re.compile(r"\b(?:vector|component|resolve|resolving)\b", re.IGNORECASE)
_LOG_EXP = re.compile(r"\\(?:ln|log|exp)|\b(?:e\^|10\^|log_)\b")
_TRIG = re.compile(r"\\(?:sin|cos|tan|csc|sec|cot)|\b(?:sin|cos|tan)\b", re.IGNORECASE)
_CALCULUS = re.compile(r"\\(?:int|dfrac\{d|partial)|\b(?:derivative|integrate|d/dx)\b", re.IGNORECASE)


def extract_features(question: dict[str, Any]) -> Features:
    """Pull structural signals from the question stem + worked solution.

    Structural difficulty signals live in BOTH the stem/options and the
    explanation. We scan a combined text for algebraic/arithmetic/trig/
    calculus patterns so the scorer remains useful even when a worked
    solution is absent (e.g. when ranking freshly-generated candidates
    before the reviewer writes the explanation). Step count still comes
    only from the explanation, since that is where steps appear.
    """
    stem = str(question.get("question_text", ""))
    explanation = str(question.get("explanation", ""))
    options = question.get("options", {})

    f = Features()
    f.stem_chars = len(stem.strip())
    f.stem_clauses = max(1, len(_CLAUSE_SPLIT.split(stem.strip())))

    opt_text = ""
    if isinstance(options, dict):
        f.option_count = len(options)
        opt_text = " ".join(str(v) for v in options.values())
        if _ROMAN_OPTION.search(opt_text):
            f.multi_statement_options = True

    # Combined text — scanned for algebraic/arithmetic/trig/calculus signals.
    combined = f"{stem}\n{opt_text}\n{explanation}"

    # Solution steps — count worked-solution steps. Preference order:
    #   1. Explicit markers ("1.", "-", "Step N:") — strongest signal.
    #   2. Blank-line separated blocks — generator writes one block per step.
    #   3. Sentence count — fallback for paragraph-style explanations.
    if explanation.strip():
        marker_steps = [s for s in _STEP_MARKERS.split(explanation) if s.strip()]
        if len(marker_steps) >= 2:
            f.solution_steps = len(marker_steps)
        else:
            blocks = [b for b in re.split(r"\n\s*\n+", explanation) if b.strip()]
            if len(blocks) >= 2:
                f.solution_steps = len(blocks)
            else:
                # Count sentence breaks (period+space+capital/dollar/backslash).
                sentences = max(1, len(_STEP_SENTENCE.findall(explanation)) + 1)
                f.solution_steps = sentences
    else:
        f.solution_steps = 1

    f.arithmetic_ops = len(_ARITH.findall(combined))
    f.has_quadratic = bool(_QUADRATIC.search(combined))
    f.has_simultaneous = bool(_SIMULTANEOUS.search(combined))
    f.has_compound_fraction = bool(_COMPOUND_FRAC.search(combined))
    f.has_vector_decomp = bool(_VECTOR.search(combined))
    f.has_log_exp = bool(_LOG_EXP.search(combined))
    f.has_trig = bool(_TRIG.search(combined))
    f.has_calculus = bool(_CALCULUS.search(combined))
    return f


# ──────────────────────────────────────────────────────────────────────────
# Scoring
# ──────────────────────────────────────────────────────────────────────────


def score(question: dict[str, Any]) -> tuple[float, str, Features]:
    """Return (score_0_to_1, band, features).

    The score is a weighted sum of structural signals. Weights are
    calibrated so a "typical" Easy question (1 step, no algebra) scores
    ~0.20 and a Hard multi-stage algebraic question scores ~0.75.
    """
    f = extract_features(question)

    # Step count: 1 step = 0.0, 2 = 0.10, 3 = 0.18, 4 = 0.24, 5+ = 0.30 (capped)
    step_score = min(0.30, max(0.0, (f.solution_steps - 1) * 0.08))

    # Arithmetic density: 0–2 ops = 0.0, ramping to 0.15 at 10+ ops.
    arith_score = min(0.15, max(0.0, (f.arithmetic_ops - 2) * 0.02))

    # Algebraic complexity: each advanced pattern adds a fixed bump.
    algebra_score = 0.0
    if f.has_quadratic:
        algebra_score += 0.10
    if f.has_simultaneous:
        algebra_score += 0.12
    if f.has_compound_fraction:
        algebra_score += 0.06
    if f.has_vector_decomp:
        algebra_score += 0.10
    if f.has_log_exp:
        algebra_score += 0.08
    if f.has_trig:
        algebra_score += 0.05
    if f.has_calculus:
        algebra_score += 0.12
    algebra_score = min(algebra_score, 0.30)

    # Reading complexity: long stems + multi-statement options add load.
    reading_score = 0.0
    if f.stem_chars > 280:
        reading_score += 0.06
    if f.stem_chars > 520:
        reading_score += 0.06
    if f.stem_clauses >= 4:
        reading_score += 0.04
    if f.multi_statement_options:
        reading_score += 0.08
    reading_score = min(reading_score, 0.20)

    total = step_score + arith_score + algebra_score + reading_score
    total = max(0.0, min(1.0, total))

    band = "Easy"
    for threshold, name in SCORE_BANDS:
        if total < threshold:
            band = name
            break
    else:
        band = "Very Hard"

    # Attach component breakdown for debugging + the correlation test.
    f.extra = {
        "step_score": round(step_score, 3),
        "arith_score": round(arith_score, 3),
        "algebra_score": round(algebra_score, 3),
        "reading_score": round(reading_score, 3),
    }
    return round(total, 4), band, f


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def _load_question(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data:
        return data["questions"][0]
    return data


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Score structural difficulty of an ESAT question")
    p.add_argument("--question", type=Path, required=True)
    p.add_argument("--label", default=None, help="optional human label for correlation testing")
    args = p.parse_args(argv)

    q = _load_question(args.question)
    s, band, f = score(q)
    print(json.dumps({
        "score": s,
        "band": band,
        "features": {
            "stem_chars": f.stem_chars,
            "stem_clauses": f.stem_clauses,
            "option_count": f.option_count,
            "multi_statement_options": f.multi_statement_options,
            "solution_steps": f.solution_steps,
            "arithmetic_ops": f.arithmetic_ops,
            "has_quadratic": f.has_quadratic,
            "has_simultaneous": f.has_simultaneous,
            "has_compound_fraction": f.has_compound_fraction,
            "has_vector_decomp": f.has_vector_decomp,
            "has_log_exp": f.has_log_exp,
            "has_trig": f.has_trig,
            "has_calculus": f.has_calculus,
            "components": f.extra,
        },
        "human_label": args.label,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
