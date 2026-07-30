#!/usr/bin/env python3
"""
Structural Difficulty Scorer — Layer 4 of the verification stack (ESA-45).

A deterministic 6-feature scorer that estimates question difficulty from the
worked solution and options. It produces a 1–10 **structural** score to sit
alongside the LLM self-assessment (`difficulty_score`). Comparing the two
later tells us which better predicts real exam performance.

Features (each → a 0..1 "hardness" contribution):

1. **reasoning_steps**    — distinct steps in the worked solution.
2. **concept_integration** — distinct concepts referenced.
3. **distractor_closeness** — 1 − normalised Levenshtein distance between the
   correct option text and its nearest distractor. Closer = harder.
4. **context_novelty**    — standard textbook setup vs. novel real-world context.
5. **trap_presence**      — count of identifiable misconception traps.
6. **option_format**      — algebraic > numeric > conceptual/qualitative.

Weighted combination → `difficulty_score_structural` ∈ [1, 10].

Because this is a *scorer* (not a gate), `check()` always passes; the verdict
`score` carries the normalised structural difficulty (0..1) and the raw 1–10
value is attached as `difficulty_score_structural`.

Standard verdict dict:

    {
        "pass": True,
        "score": float,                    # structural / 10.0
        "reason": str,
        "issues": [],
        "cost_usd": 0.0,
        "gate": "structural_difficulty",
        "difficulty_score_structural": float,   # 1..10
        "features": {...},                       # raw feature values
    }

Usage:
    python structural_difficulty.py --question path/to/q.json
    python structural_difficulty.py --self-test
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
else:
    from .verdict import verdict  # type: ignore


# ---------------------------------------------------------------------------
# Feature weights (sum to 1.0)
# ---------------------------------------------------------------------------

WEIGHTS = {
    "reasoning_steps": 0.25,
    "concept_integration": 0.20,
    "distractor_closeness": 0.15,
    "context_novelty": 0.10,
    "trap_presence": 0.15,
    "option_format": 0.15,
}

# Concept lexicon — keyword families that signal a distinct concept.
CONCEPT_LEXICON = [
    # Mechanics
    "kinematic", "velocity", "acceleration", "force", "newton", "momentum",
    "impulse", "energy", "kinetic", "potential", "work", "power", "torque",
    "moment", "friction", "tension", "gravity", "gravitational", "projectile",
    "circular", "orbit", "spring", "hooke",
    # Electricity / fields
    "electric", "charge", "current", "voltage", "resistance", "capacitor",
    "magnetic", "flux", "field", "potential difference", "circuit", "ohm",
    # Waves / thermal / quantum
    "wave", "frequency", "wavelength", "interference", "diffraction",
    "refraction", "photon", "quantum", "photoelectric", "thermal",
    "temperature", "entropy", "heat", "gas", "pressure",
    # Chemistry
    "mole", "molar", "stoichiometr", "concentration", "equilibrium",
    "acid", "base", "oxidation", "reduction", "redox", "bond", "enthalpy",
    "rate", "catalyst", "ion", "electron", "valenc", "periodic",
    # Biology
    "cell", "membrane", "enzyme", "protein", "dna", "rna", "gene",
    "chromosome", "mitosis", "meiosis", "respiration", "photosynthesis",
    "neuron", "hormone", "immune", "evolution", "enzyme",
    # Maths
    "algebra", "inequality", "quadratic", "polynomial", "logarithm", "exponent",
    "trigonometr", "geometr", "vector", "matrix", "differentiat", "integral",
    "derivative", "probability", "statistic", "binomial", "seri", "sequence",
    "surds", "function", "graph",
]


# Misconception trap indicators (in distractor analysis / distractor text).
TRAP_PATTERNS = re.compile(
    r"(forgot(?:ten)?|fail(?:ed|ing)? to|instead of|mistaken|confus(?:e|ed|ing)|"
    r"g\s*/\s*2|half of g|sign error|wrong sign|sine|cosine|tangent|"
    r"radius|diameter|mass|weight|squar(?:e|ed)|square root|2\s*\\?pi|"
    r"reciprocal|inverted|numerator|denominator|unit(?:s)? conversion|"
    r"magnitude|direction|parallel|series|positive|negative)",
    re.IGNORECASE,
)

# Markers of a novel / unusual real-world context (harder).
NOVELTY_MARKERS = re.compile(
    r"\b(Olympic|NASA|Mars|Jupiter|asteroid|skyscraper|submarine|"
    r"roller[ -]?coaster|bungee|spacecraft|satellite|volcano|tsunami|"
    r"Company|[A-Z][a-z]+Corp|brand|patent|experiment|investigation|"
    r"researcher|scientist|unusual|novel|bizarre|peculiar|hypothetical|"
    r"imaginary|fictional)\b"
)

OPTION_LETTER_RE = re.compile(r"^[A-I]$")

# A numeric answer: digits, decimal, unit, simple arithmetic/surd. No variables.
NUMERIC_RE = re.compile(r"^-?[\d.,]+\s*(?:[a-zA-Z²³⁻¹/]*)?$|^-?[\d.]+\s*[×√]")
# An algebraic answer: contains a variable or an inequality/relation symbol.
ALGEBRAIC_RE = re.compile(r"[a-zA-Z]\s*[<>=≤≥]|^[A-Za-z]\w*\s*$|surds|√|\\frac|\\sqrt|[<>]")


# ---------------------------------------------------------------------------
# Levenshtein distance (no external dependency)
# ---------------------------------------------------------------------------

def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cur[j] = min(
                prev[j] + 1,
                cur[j - 1] + 1,
                prev[j - 1] + (0 if ca == cb else 1),
            )
        prev = cur
    return prev[-1]


# ---------------------------------------------------------------------------
# Question helpers
# ---------------------------------------------------------------------------

def _options_map(question: dict[str, Any]) -> dict[str, str]:
    opts = question.get("options")
    if isinstance(opts, dict):
        return {str(k).upper(): str(v) for k, v in opts.items()}
    if isinstance(opts, list):
        letters = "ABCDEFGHI"
        return {letters[i]: str(v) for i, v in enumerate(opts) if i < len(letters)}
    return {}


def _correct_text(question: dict[str, Any]) -> str:
    opts = _options_map(question)
    ca = str(question.get("correct_answer", "")).strip().upper()
    if ca in opts:
        return opts[ca]
    return str(question.get("correct_answer", ""))


def _distractors(question: dict[str, Any]) -> list[str]:
    opts = _options_map(question)
    ca = str(question.get("correct_answer", "")).strip().upper()
    return [v for k, v in opts.items() if k != ca]


def _solution_text(question: dict[str, Any]) -> str:
    return str(
        question.get("worked_solution")
        or question.get("explanation")
        or ""
    )


# ---------------------------------------------------------------------------
# Feature scorers (each returns a 0..1 hardness value + raw detail)
# ---------------------------------------------------------------------------

def _feature_reasoning_steps(solution: str) -> tuple[float, int]:
    """Count distinct reasoning steps: numbered items, equation lines, paragraphs."""
    lines = [ln.strip() for ln in solution.splitlines() if ln.strip()]
    numbered = len(re.findall(r"(?m)^\s*\d+[\.\)]\s", solution))
    equations = sum(1 for ln in lines if "=" in ln and len(ln) < 120)
    paragraphs = max(1, len(re.split(r"\n\s*\n", solution.strip())) if solution.strip() else 0)
    steps = max(numbered, min(equations, numbered + equations + 1), paragraphs)
    # Saturate at 8 steps.
    hardness = min(1.0, steps / 8.0)
    return hardness, steps


def _feature_concept_integration(text: str) -> tuple[float, int]:
    """Count distinct concept families referenced anywhere in the question."""
    blob = (text or "").lower()
    matched = set()
    for concept in CONCEPT_LEXICON:
        if concept in blob:
            matched.add(concept.split()[0])
    count = len(matched)
    hardness = min(1.0, count / 5.0)
    return hardness, count


def _feature_distractor_closeness(correct: str, distractors: list[str]) -> tuple[float, float]:
    """Nearest distractor by normalised edit distance → closeness = hardness."""
    if not correct or not distractors:
        # No closeness signal; neutral.
        return 0.3, 0.3
    best_closeness = 0.0
    for d in distractors:
        a, b = correct.strip().lower(), d.strip().lower()
        if not a or not b:
            continue
        dist = _levenshtein(a, b)
        norm = dist / max(len(a), len(b))
        closeness = 1.0 - norm
        best_closeness = max(best_closeness, closeness)
    return best_closeness, round(best_closeness, 3)


def _feature_context_novelty(question_text: str, solution: str) -> tuple[float, int]:
    blob = f"{question_text} {solution}"
    markers = len(NOVELTY_MARKERS.findall(blob))
    hardness = min(1.0, markers / 3.0)
    return hardness, markers


def _feature_trap_presence(question: dict[str, Any]) -> tuple[float, int]:
    """Count misconception traps referenced in distractor analysis / distractor text."""
    trap_text_parts: list[str] = []
    meta = question.get("metadata") or {}
    da = None
    if isinstance(meta, dict):
        da = meta.get("distractor_analysis")
    if not da:
        da = question.get("distractor_analysis")
    if isinstance(da, dict):
        trap_text_parts.extend(str(v) for v in da.values())
    # Also scan distractor option text and the explanation tail.
    trap_text_parts.extend(_distractors(question))
    trap_text_parts.append(_solution_text(question))
    blob = "\n".join(trap_text_parts)
    count = len(set(m.group(1).lower() for m in TRAP_PATTERNS.finditer(blob)))
    hardness = min(1.0, count / 4.0)
    return hardness, count


def _feature_option_format(correct_text: str) -> tuple[float, str]:
    """algebraic (1.0) > numeric (0.5) > conceptual (0.2)."""
    t = correct_text.strip()
    if not t:
        return 0.3, "unknown"
    # Conceptual: a full sentence / long phrase of words.
    words = re.findall(r"[A-Za-z]{2,}", t)
    digit_ratio = len(re.findall(r"\d", t)) / max(1, len(t))
    if len(words) >= 4 and digit_ratio < 0.15:
        return 0.2, "conceptual"
    if ALGEBRAIC_RE.search(t) and digit_ratio < 0.4:
        return 1.0, "algebraic"
    if NUMERIC_RE.match(t) or digit_ratio >= 0.3:
        return 0.5, "numeric"
    return 0.4, "mixed"


# ---------------------------------------------------------------------------
# Core scorer
# ---------------------------------------------------------------------------

def score(question: dict[str, Any]) -> dict[str, Any]:
    """Compute the 6-feature structural difficulty. Always succeeds."""
    solution = _solution_text(question)
    blob = "\n".join([
        str(question.get("question_text", "")),
        " ".join(_options_map(question).values()),
        solution,
    ])

    correct_text = _correct_text(question)
    distractors = _distractors(question)

    h_steps, n_steps = _feature_reasoning_steps(solution)
    h_concepts, n_concepts = _feature_concept_integration(blob)
    h_close, raw_close = _feature_distractor_closeness(correct_text, distractors)
    h_novelty, n_markers = _feature_context_novelty(
        str(question.get("question_text", "")), solution
    )
    h_traps, n_traps = _feature_trap_presence(question)
    h_format, fmt_label = _feature_option_format(correct_text)

    hardness = (
        WEIGHTS["reasoning_steps"] * h_steps
        + WEIGHTS["concept_integration"] * h_concepts
        + WEIGHTS["distractor_closeness"] * h_close
        + WEIGHTS["context_novelty"] * h_novelty
        + WEIGHTS["trap_presence"] * h_traps
        + WEIGHTS["option_format"] * h_format
    )
    hardness = max(0.0, min(1.0, hardness))
    structural = round(1.0 + 9.0 * hardness, 1)  # 1..10

    features = {
        "reasoning_steps": {"hardness": round(h_steps, 3), "steps": n_steps},
        "concept_integration": {"hardness": round(h_concepts, 3), "concepts": n_concepts},
        "distractor_closeness": {"hardness": round(h_close, 3), "closeness": raw_close},
        "context_novelty": {"hardness": round(h_novelty, 3), "markers": n_markers},
        "trap_presence": {"hardness": round(h_traps, 3), "traps": n_traps},
        "option_format": {"hardness": round(h_format, 3), "format": fmt_label},
    }

    return {
        "difficulty_score_structural": structural,
        "hardness": round(hardness, 4),
        "features": features,
    }


def check(question: dict[str, Any]) -> dict[str, Any]:
    """Verdict-compatible wrapper. Scorer never rejects → pass=True."""
    result = score(question)
    structural = result["difficulty_score_structural"]
    band = (
        "easy" if structural < 3.5
        else "medium" if structural < 6.5
        else "hard" if structural < 8.5
        else "very_hard"
    )
    return verdict(
        passed=True,
        score=round(structural / 10.0, 4),
        reason=f"structural difficulty {structural}/10 ({band})",
        issues=[],
        cost_usd=0.0,
        gate="structural_difficulty",
        difficulty_score_structural=structural,
        hardness=result["hardness"],
        features=result["features"],
        difficulty_band_structural=band,
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

SELF_TEST_CASES = [
    ("trivial_single_step",
     {"question_text": "What is 2 + 2?",
      "options": {"A": "4", "B": "3", "C": "5", "D": "6"},
      "correct_answer": "A",
      "explanation": "2 + 2 = 4"},
     "expect_low"),
    ("hard_multi_concept",
     {"question_text": "A projectile is launched on an incline. Using conservation of energy "
                       "and kinematics, find the range. Olympic ski jump context.",
      "options": {"A": "12 m", "B": "13 m", "C": "12.5 m", "D": "12.0 m"},
      "correct_answer": "A",
      "explanation": "1. Apply conservation of energy: mg h = 1/2 m v^2.\n"
                     "2. Use kinematics to find the time of flight.\n"
                     "3. Resolve components of velocity.\n"
                     "4. Combine to get range R = v^2 sin(2θ)/g.",
      "metadata": {"distractor_analysis": {
          "B": "forgot to square the velocity",
          "C": "used diameter instead of radius and confused sine/cosine",
          "D": "mass vs weight confusion"}}},
     "expect_high"),
]


def _run_self_test() -> int:
    failures = 0
    for name, q, expectation in SELF_TEST_CASES:
        r = score(q)
        s = r["difficulty_score_structural"]
        ok = (expectation == "expect_low" and s < 4.0) or (expectation == "expect_high" and s >= 5.0)
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {name}: structural={s} hardness={r['hardness']} ({expectation})")
        if not ok:
            print(f"        features={json.dumps(r['features'])}")
            failures += 1
    print(f"\n{len(SELF_TEST_CASES) - failures}/{len(SELF_TEST_CASES)} cases passed")
    return failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_question(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data and isinstance(data["questions"], list):
        return data["questions"][0]
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT structural difficulty scorer (Layer 4)")
    p.add_argument("--question", type=Path, help="Path to a question JSON file")
    p.add_argument("--self-test", action="store_true", help="Run built-in test cases")
    args = p.parse_args(argv)

    if args.self_test:
        return _run_self_test()

    if not args.question:
        p.error("--question or --self-test is required")

    question = _load_question(args.question)
    print(json.dumps(check(question), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
