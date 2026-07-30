#!/usr/bin/env python3
"""
ESAT Calculator-Free Arithmetic Checker (Gate 1 of the 4-gate stack).

ESAT is strictly no-calculator. This gate rejects worked solutions that
require non-perfect-square roots, non-standard trig angles, 3+ decimal
arithmetic, or a value of g other than 10 m/s². See:

- `calculator-free-research.md`
- `orchestration-review.md` Top Priority #1

Standard verdict dict:

    {
        "pass": bool,
        "score": float,        # 1.0 clean / 0.5 issues-but-maybe-mental / 0.0 hard fail
        "reason": str,
        "issues": list[str],
        "cost_usd": 0.0,       # deterministic — no API call
    }

Usage:
    python calculator_check.py --question path/to/q.json
    python calculator_check.py --self-test
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable

# Make sibling imports work both as package and as flat scripts.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
else:
    from .verdict import verdict  # type: ignore


# ---------------------------------------------------------------------------
# ESAT calculator-free rules (sourced from calculator-free-research.md §1)
# ---------------------------------------------------------------------------

G_VALUE_REQUIRED = 10.0  # P3.5b — g = 10 N kg⁻¹ on Earth

PERFECT_SQUARES = {i * i for i in range(16)}  # 0..225
COMMON_SURDS = {2, 3, 5, 6, 7}  # √2..√7 appear un-simplified as final answers
STANDARD_TRIG_ANGLES = {0, 30, 45, 60, 90, 180, 270, 360}
MAX_DECIMAL_PLACES = 2  # M2.13 — final answers rounded to ≤2 dp

# Multiplications that are borderline mental: 12 × 20 = 240.
MAX_MENTAL_FACTOR = 20

# Regex patterns that flag potentially calculator-dependent content.
TRIG_ANGLE_RE = re.compile(
    r"\b(?:sin|cos|tan)\s*[\(\{]?\s*(-?\d+(?:\.\d+)?)\s*[°\)]",
    re.IGNORECASE,
)
SQRT_RE = re.compile(r"(?:√|sqrt)\s*[\(\{]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
LOG_RE = re.compile(r"\b(?:log|ln|log_?10|log_?2)\s*[\(\{]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
LONG_DECIMAL_RE = re.compile(r"\d+\.\d{3,}")
MULTIPLY_RE = re.compile(r"(\d{2,3})\s*[×x\*]\s*(\d{2,3})")
G_VALUE_RE = re.compile(r"\bg\s*=\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
G_USAGE_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:N/kg|m/s\^?2|m\s*s\^-?2)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flatten_question(question: dict[str, Any]) -> str:
    """Concatenate the question text, options, and worked solution."""
    parts: list[str] = [str(question.get("question_text", ""))]

    options = question.get("options")
    if isinstance(options, dict):
        parts.append(" ".join(str(v) for v in options.values()))
    elif isinstance(options, list):
        parts.append(" ".join(str(v) for v in options))

    parts.append(str(question.get("worked_solution", "") or question.get("explanation", "")))
    return "\n".join(parts)


def _is_mental_multiplication(a: int, b: int) -> bool:
    """True if `a × b` is reasonable to compute mentally."""
    if a <= 12 or b <= 12:
        return True
    # 12 × 20 is fine, 25 × 30 is borderline, 37 × 43 is not.
    if (a <= MAX_MENTAL_FACTOR and b <= MAX_MENTAL_FACTOR) and (
        a in (10, 15, 20, 25) or b in (10, 15, 20, 25) or a % 10 == 0 or b % 10 == 0
    ):
        return True
    return False


def _is_clean_root(n: float) -> bool:
    """True if √n is mental (perfect square, common surd, or trivial)."""
    if n < 0:
        return False
    if n in PERFECT_SQUARES:
        return True
    if n <= 10 and int(n) in COMMON_SURDS:
        # Common surds (√2,√3,√5,√6,√7) appear un-simplified in answers.
        return True
    return False


def _is_standard_angle(deg: float) -> bool:
    return deg in STANDARD_TRIG_ANGLES or (deg % 90 == 0)


def _is_clean_log_arg(n: float) -> bool:
    """`log10(1000)=3` is mental. `log10(7)` is not."""
    if n <= 0:
        return False
    if abs(n - 10 ** round(math.log10(n))) < 1e-9:
        return True
    # log_2(8)=3, log_2(32)=5, …
    for base in (2.0, 3.0, 5.0):
        if math.log(n, base).is_integer():
            return True
    return False


# ---------------------------------------------------------------------------
# Core checks
# ---------------------------------------------------------------------------

def _check_trig_angles(text: str) -> list[str]:
    issues: list[str] = []
    for m in TRIG_ANGLE_RE.finditer(text):
        fn = m.group(0).lower().split("(")[0].split("{")[0].strip()
        deg = float(m.group(1))
        if not _is_standard_angle(deg):
            issues.append(
                f"Non-standard trig angle '{m.group(0).strip()}' "
                f"(allowed: {sorted(STANDARD_TRIG_ANGLES)})"
            )
    return issues


def _check_roots(text: str) -> list[str]:
    issues: list[str] = []
    for m in SQRT_RE.finditer(text):
        n = float(m.group(1))
        if not _is_clean_root(n):
            issues.append(
                f"Non-perfect square root '{m.group(0).strip()}' requires calculator"
            )
    return issues


def _check_logs(text: str) -> list[str]:
    issues: list[str] = []
    for m in LOG_RE.finditer(text):
        n = float(m.group(1))
        if not _is_clean_log_arg(n):
            issues.append(
                f"Logarithm '{m.group(0).strip()}' requires calculator to evaluate"
            )
    return issues


def _check_long_decimals(text: str) -> list[str]:
    issues: list[str] = []
    for m in LONG_DECIMAL_RE.finditer(text):
        # ignore numbers clearly within a year / id
        if re.match(r"^(19|20)\d{2}\.", m.group(0)):
            continue
        issues.append(
            f"Value '{m.group(0).strip()}' has 3+ decimal places — not mental"
        )
    return issues


def _check_multiplications(text: str) -> list[str]:
    issues: list[str] = []
    for m in MULTIPLY_RE.finditer(text):
        a, b = int(m.group(1)), int(m.group(2))
        if not _is_mental_multiplication(a, b):
            issues.append(
                f"Multiplication '{a}×{b}' is not reasonable to do mentally"
            )
    return issues


def _check_g_value(text: str) -> list[str]:
    """Reject g = 9.8 / 9.81 / 9.81 m/s² (ESAT mandates g = 10)."""
    issues: list[str] = []
    for m in G_VALUE_RE.finditer(text):
        val = float(m.group(1))
        if abs(val - G_VALUE_REQUIRED) > 0.01 and val in (9.8, 9.81, 9.80, 9.6, 9.7):
            issues.append(
                f"g = {val} violates ESAT convention (P3.5b mandates g = 10 N kg⁻¹)"
            )
    # Bare "9.81 m/s²" without an explicit g=
    for m in re.finditer(r"\b(9\.8\d*)\s*(?:N/kg|m/s\^?2|m\s*s\^-?2)", text):
        issues.append(
            f"Gravitational acceleration '{m.group(0).strip()}' should be 10 N kg⁻¹"
        )
    return issues


CHECKS = (
    ("trig", _check_trig_angles),
    ("roots", _check_roots),
    ("logs", _check_logs),
    ("decimals", _check_long_decimals),
    ("multiplications", _check_multiplications),
    ("g_value", _check_g_value),
)


def check(question: dict[str, Any]) -> dict[str, Any]:
    """Run all calculator-free checks against a single question.

    The question dict follows the corpus schema:
        {
          "question_text": str,
          "options": {"A": str, "B": str, ...} | [str, ...],
          "worked_solution": str,
          ...
        }
    """
    text = _flatten_question(question)
    all_issues: list[str] = []
    for _, fn in CHECKS:
        all_issues.extend(fn(text))

    if not all_issues:
        return verdict(
            passed=True,
            score=1.0,
            reason="No calculator-dependent arithmetic detected",
            issues=[],
            cost_usd=0.0,
            gate="calculator_check",
        )

    # Hard fails (roots / trig / logs / g_value) vs. soft (decimals / mult).
    hard = [
        i for i in all_issues
        if any(k in i for k in ("root", "trig", "Logarithm", "g = ", "gravit"))
    ]
    score = 0.0 if hard else 0.5
    return verdict(
        passed=False,
        score=score,
        reason=(
            f"{len(hard)} hard + {len(all_issues) - len(hard)} soft "
            "calculator-dependent issue(s)"
        ),
        issues=all_issues,
        cost_usd=0.0,
        gate="calculator_check",
    )


# ---------------------------------------------------------------------------
# Self-test — 10+ cases covering pass + fail of each rule
# ---------------------------------------------------------------------------

SELF_TEST_CASES = [
    # (name, question, expected_pass)
    (
        "perfect_square_root",
        {"question_text": "Simplify √81.", "options": {"A": "9"}, "worked_solution": "9 × 9 = 81"},
        True,
    ),
    (
        "common_surd_answer",
        {"question_text": "Find the magnitude.", "options": {"A": "2√3"}, "worked_solution": ""},
        True,
    ),
    (
        "standard_trig_only",
        {
            "question_text": "A ramp at 30°. Find sin(30°).",
            "options": {"A": "0.5"},
            "worked_solution": "sin(30°) = 1/2",
        },
        True,
    ),
    (
        "g_equals_ten",
        {
            "question_text": "A 2 kg mass falls. Find the force.",
            "options": {"A": "20 N"},
            "worked_solution": "F = mg = 2 × 10 = 20 N",
        },
        True,
    ),
    (
        "two_dp_decimal_ok",
        {
            "question_text": "What is 0.25 + 0.5?",
            "options": {"A": "0.75"},
            "worked_solution": "Add: 0.25 + 0.50 = 0.75",
        },
        True,
    ),
    (
        "non_perfect_square_root_fail",
        {"question_text": "Find √17.", "options": {"A": "4.123"}, "worked_solution": "√17 ≈ 4.123"},
        False,
    ),
    (
        "non_standard_trig_angle",
        {"question_text": "Find sin(23°).", "options": {"A": "0.39"}, "worked_solution": "sin(23°)"},
        False,
    ),
    (
        "ugly_decimal_fail",
        {"question_text": "What is 7.382 m/s?", "options": {"A": "7.382"}, "worked_solution": ""},
        False,
    ),
    (
        "ugly_multiplication_fail",
        {"question_text": "Compute 37 × 43.", "options": {"A": "1591"}, "worked_solution": "37 × 43 = 1591"},
        False,
    ),
    (
        "g_value_nine_point_eight_fail",
        {
            "question_text": "Falling mass, use g = 9.81.",
            "options": {"A": "19.62 N"},
            "worked_solution": "F = 2 × 9.81 = 19.62",
        },
        False,
    ),
    (
        "log_calculator_fail",
        {"question_text": "Compute log(7).", "options": {"A": "0.845"}, "worked_solution": "log(7)"},
        False,
    ),
    (
        "log_power_of_two_ok",
        {"question_text": "Compute log_2(8).", "options": {"A": "3"}, "worked_solution": "2^3 = 8"},
        True,
    ),
]


def _run_self_test() -> int:
    failures = 0
    for name, q, expected in SELF_TEST_CASES:
        result = check(q)
        ok = result["pass"] == expected
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {name}: pass={result['pass']} expected={expected}")
        if not ok:
            for issue in result["issues"]:
                print(f"        - {issue}")
            failures += 1
    print(f"\n{len(SELF_TEST_CASES) - failures}/{len(SELF_TEST_CASES)} cases passed")
    return failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_question(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Accept either a single question or a corpus file with `questions`.
    if isinstance(data, dict) and "questions" in data and isinstance(data["questions"], list):
        return data["questions"][0]
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT calculator-free checker")
    p.add_argument("--question", type=Path, help="Path to a question JSON file")
    p.add_argument("--self-test", action="store_true", help="Run built-in test cases")
    args = p.parse_args(argv)

    if args.self_test:
        return _run_self_test()

    if not args.question:
        p.error("--question or --self-test is required")

    question = _load_question(args.question)
    result = check(question)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
