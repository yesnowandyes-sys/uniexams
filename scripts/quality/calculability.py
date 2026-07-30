#!/usr/bin/env python3
"""
ESAT Calculability Checker — Layer 1 of the verification stack (ESA-45).

ESAT is strictly calculator-free. This gate inspects the question text,
options, and worked solution for arithmetic that a candidate cannot
reasonably perform mentally. It has two tiers:

* **Tier 1 — REJECT** (hard failures): the question is discarded.
* **Tier 2 — WARN**  (soft flags): the question is accepted but flagged for
  potential human review.

A question passes the gate iff it has **zero Tier 1** issues. Tier 2 issues
are reported in `issues` but do not fail the gate.

Spec: ESA-45 / TASKS/03-generation-and-verification.md §Layer 1. Replaces the
ad-hoc rule list in the legacy `calculator_check.py` with the explicit tiered
rule set requested for the rebuilt pipeline.

Standard verdict dict:

    {
        "pass": bool,            # False iff any Tier 1 issue
        "score": float,          # 1.0 clean / 0.5 warn-only / 0.0 hard fail
        "reason": str,
        "issues": list[str],     # Tier 1 + Tier 2 findings
        "cost_usd": 0.0,         # deterministic — no API call
        "gate": "calculability",
        "tier1": list[str],      # hard rejects
        "tier2": list[str],      # soft warnings
    }

Usage:
    python calculability.py --question path/to/q.json
    python calculability.py --self-test
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

# Make sibling imports work both as a package and as flat scripts.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
else:
    from .verdict import verdict  # type: ignore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

G_CANONICAL = 10.0          # ESAT mandates g = 10 N kg⁻¹.
G_ACCEPTABLE_IF_GIVEN = 9.81  # permitted only when stated explicitly in the stem

STANDARD_ANGLES = {0, 30, 45, 60, 90, 180, 270, 360}

PERFECT_SQUARES = {i * i for i in range(32)}
# Surds that may appear un-simplified as final answers (√2..√7, √10).
COMMON_SURDS = {2, 3, 5, 6, 7, 10}

MAX_SIG_FIGS = 3            # Tier 1: answers needing > 3 sig figs are rejected
MAX_DECIMAL_PLACES = 2      # Tier 1: non-terminating decimals beyond 2 dp
PRODUCT_HARD_THRESHOLD = 15  # both factors above this w/o nice structure → reject

# Named physical constants that MUST be provided in the stem if used.
PHYSICAL_CONSTANT_NAMES = re.compile(
    r"\b("
    r"boltzmann|stefan|planck(?:'s)? constant|reduced planck|"
    r"avogadro|gas constant|molar gas|"
    r"speed of light|permeability of free space|permittivity of free space|"
    r"electron mass|proton mass|neutron mass|atomic mass unit|"
    r"elementary charge|faraday constant|rydberg|"
    r"coulomb constant|gravitational constant|specific heat capacity (?:of|for)"
    r")\b",
    re.IGNORECASE,
)

# Non-SI units that require conversion (Tier 2 warning).
NON_SI_UNITS = re.compile(
    r"\b(mile|feet|foot|inch|inches|pound|pounds|lb|oz|"
    r"°?F(ahrenheit)?|gallon|ounce|stone|acre|yard)\b",
    re.IGNORECASE,
)

# Compound units written with a slash, e.g. "m/s", "kg/m^3" (Tier 2).
SLASH_UNIT_RE = re.compile(r"\b(m|kg|s|N|Pa|J|W|C|V|Hz|mol|K|g|A)\s*/\s*(m|kg|s|N|Pa|J|W|C|V|Hz|mol|K|g|A)(?:\s*\^?\s*-?\d+)?", re.IGNORECASE)

# Fractions like 7/13 or "denominator". Match "a/b" where b is an integer.
FRACTION_RE = re.compile(r"(?<![/\w])\b\d+\s*/\s*(\d{1,4})\b")


# Detection regexes
TRIG_ANGLE_RE = re.compile(
    r"\b(?:sin|cos|tan)\s*[\(\{]?\s*(-?\d+(?:\.\d+)?)\s*°",
    re.IGNORECASE,
)
SQRT_RE = re.compile(r"(?:√|sqrt\s*\()\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
LOG_RE = re.compile(r"\b(?:log|ln|log_?10|log_?2)\s*[\(\{]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
# Negative lookbehind: don't match ``g`` that is part of an algebraic
# expression (e.g. ``W/g = 4.0`` in a worked solution), where the number is
# the value of the expression, not the gravitational constant. Without this,
# a correct stem stating "Take g = 10" alongside "m = W/g = 4.0/10" was
# falsely rejected as "g = 4.0" (ESA-52 smoke-test finding).
G_ASSIGN_RE = re.compile(r"(?<![\w/*])g\s*=\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
G_BARE_RE = re.compile(r"\b(9\.\d{1,3})\s*(?:N\s*/\s*kg|m\s*/\s*s\^?2|m\s*s\s*\^?-?2)", re.IGNORECASE)
MULTIPLY_RE = re.compile(r"(\d{1,3})\s*(?:×|x|\*)\s*(\d{1,3})")
DECIMAL_RE = re.compile(r"(?<![\d.])(\d+\.\d+)(?![\d.])")

# ESA-55: the generator ``explanation`` appends a "Why the other options are
# wrong" section after the correct derivation. That section deliberately
# contains *wrong* values (e.g. ``g = 0.1`` instead of ``g = 10``, or
# ``0.00005 cm²``) describing distractors. Scanning it produces false
# positives, so the worked-solution blob must stop at the first such header.
# Matches a header line (allowing an optional list bullet and ``**bold**``
# wrapping) whose text is the marker phrase, optionally followed by a colon.
_DISTRACTOR_HEADER_RE = re.compile(
    r"^[ \t]*(?:[-*]\s+)?(?:\*{1,2}\s*)?"
    r"(?:why the other options are wrong|incorrect(?:ly| options| answers)?)"
    r"\s*:?\s*(?:\*{1,2})?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _worked_solution(question: dict[str, Any]) -> str:
    """The correct-derivation part of the solution, distractor rationale stripped.

    A generator may supply an explicit ``worked_solution`` field (already just
    the derivation) — use it verbatim. Otherwise fall back to ``explanation``
    and cut everything from the first "Why the other options are wrong" header
    onward, since that section carries deliberately wrong distractor values.
    """
    solution = question.get("worked_solution")
    if solution:
        return str(solution)
    text = str(question.get("explanation") or "")
    m = _DISTRACTOR_HEADER_RE.search(text)
    if m:
        return text[: m.start()].rstrip()
    return text


def _flatten(question: dict[str, Any]) -> str:
    """Concatenate question text, options, and the worked solution into one blob.

    ESA-55: the worked solution is the *correct-derivation* part only — the
    "Why the other options are wrong" section is excluded so its deliberately
    wrong values are not scanned.
    """
    parts: list[str] = [str(question.get("question_text", ""))]

    options = question.get("options")
    if isinstance(options, dict):
        parts.append(" ".join(str(v) for v in options.values()))
    elif isinstance(options, list):
        parts.append(" ".join(str(v) for v in options))

    parts.append(_worked_solution(question))
    return "\n".join(parts)


def _stem(question: dict[str, Any]) -> str:
    """Just the question text + options (for 'is this given in the stem?')."""
    parts: list[str] = [str(question.get("question_text", ""))]
    options = question.get("options")
    if isinstance(options, dict):
        parts.append(" ".join(str(v) for v in options.values()))
    elif isinstance(options, list):
        parts.append(" ".join(str(v) for v in options))
    return "\n".join(parts)


def _correct_option(question: dict[str, Any]) -> str:
    """The value of the option matching ``correct_answer`` (e.g. ``"10"``)."""
    letter = str(question.get("correct_answer", "")).strip().upper()
    if not letter:
        return ""
    options = question.get("options")
    if isinstance(options, dict):
        return str(options.get(letter, "") or "")
    if isinstance(options, list):
        idx = ord(letter) - ord("A")
        if 0 <= idx < len(options):
            val = options[idx]
            return str(val) if isinstance(val, str) else str(val)
    return ""


def _correct_path(question: dict[str, Any]) -> str:
    """Blob over the *correct-answer path* only: stem text + correct option + solution.

    ESA-55: distractor options are *designed* to carry unreasonable values
    (e.g. ``0.00005 cm²``, ``g = 0.1``), so the Tier-1 decimal / sig-fig checks
    must scan only the correct option + the worked solution, never the wrong
    options. The "stem" here is the question text alone (no distractors).
    """
    parts: list[str] = [str(question.get("question_text", ""))]
    correct = _correct_option(question)
    if correct:
        parts.append(correct)
    parts.append(_worked_solution(question))
    return "\n".join(parts)


def _has_diagram(question: dict[str, Any]) -> bool:
    if question.get("has_diagram"):
        return True
    diag = str(question.get("diagram_description", "")).strip().lower()
    if diag and diag not in ("", "none", "n/a"):
        return True
    if question.get("question_images") and question.get("question_images") not in ([], "[]"):
        return True
    return False


def _sig_figs(num_str: str) -> int:
    """Count significant figures in a numeric literal string."""
    s = num_str.lstrip("0").lstrip("-")
    if "." in s:
        s = s.replace(".", "")
    s = s.lstrip("0")
    return len(s)


def _is_mental_product(a: int, b: int) -> bool:
    """True if a × b has 'nice structure' (doable mentally).

    Per ESA-45: 16 × 25 is fine, 17 × 23 is not. Nice = one factor is a
    multiple of 10 or 25, or one factor ≤ 15.
    """
    if a <= PRODUCT_HARD_THRESHOLD or b <= PRODUCT_HARD_THRESHOLD:
        return True
    for f in (a, b):
        if f % 10 == 0 or f in (25, 50, 75) or f % 25 == 0:
            return True
    return False


def _is_clean_log_arg(n: float) -> bool:
    """log(1000)=3 is mental; log(7) is not."""
    if n <= 0:
        return False
    if abs(n - 10 ** round(math.log10(n))) < 1e-9 and n >= 1:
        return True
    for base in (2.0, 3.0, 5.0):
        try:
            if math.log(n, base).is_integer():
                return True
        except (ValueError, ZeroDivisionError):
            pass
    return False


def _is_clean_root(n: float) -> bool:
    """√n is mental if a perfect square or a common small surd (√2..√7, √10)."""
    if n < 0:
        return False
    if n in PERFECT_SQUARES:
        return True
    if n <= 10 and int(round(n)) in COMMON_SURDS:
        return True
    return False


def _is_standard_angle(deg: float) -> bool:
    return deg in STANDARD_ANGLES or deg % 90 == 0


# ---------------------------------------------------------------------------
# Tier 1 checks (hard reject)
# ---------------------------------------------------------------------------

def _t1_g_value(stem: str) -> list[str]:
    """Reject g-values that aren't 10 (or 9.81 only if given in the stem).

    ESA-55: scan ``stem`` only — the question stem is where a ``g = X``
    assignment lives. A phrase like "divided by g = 0.1 instead of g = 10" in a
    worked-solution / distractor rationale is a *description* of a wrong
    answer, not an assignment, and must not be matched here.
    """
    issues: list[str] = []
    for m in G_ASSIGN_RE.finditer(stem):
        val = float(m.group(1))
        if abs(val - G_CANONICAL) < 0.01:
            continue
        if abs(val - G_ACCEPTABLE_IF_GIVEN) < 0.005 and re.search(r"\bg\s*=\s*9\.81", stem, re.IGNORECASE):
            continue  # 9.81 explicitly given in stem → allowed
        issues.append(
            f"g = {val} violates calculator-free convention (must be 10, "
            f"or 9.81 only if explicitly given in the stem)"
        )
    # Bare "9.8 N/kg" / "9.81 m/s²" with no explicit g= in the stem.
    if not re.search(r"\bg\s*=\s*9\.81", stem, re.IGNORECASE):
        for m in G_BARE_RE.finditer(stem):
            val = float(m.group(1))
            if abs(val - G_CANONICAL) > 0.01:
                issues.append(
                    f"gravitational value '{m.group(0).strip()}' is not g = 10 "
                    f"N kg⁻¹ and is not stated in the stem"
                )
    return issues


def _t1_trig_angles(full: str, has_diagram: bool) -> list[str]:
    """Reject non-standard angles unless a diagram provides estimation context."""
    issues: list[str] = []
    for m in TRIG_ANGLE_RE.finditer(full):
        deg = float(m.group(1))
        if _is_standard_angle(deg):
            continue
        if has_diagram:
            continue  # triangle diagram allows estimation
        issues.append(
            f"non-standard angle '{m.group(0).strip()}' cannot be evaluated "
            f"without a calculator (allowed: {sorted(STANDARD_ANGLES)})"
        )
    return issues


def _t1_sig_figs(full: str) -> list[str]:
    issues: list[str] = []
    for m in DECIMAL_RE.finditer(full):
        num = m.group(1)
        # Skip years / identifiers.
        if re.match(r"^(19|20)\d{2}", num):
            continue
        if _sig_figs(num) > MAX_SIG_FIGS:
            issues.append(
                f"value '{num}' requires {MAX_SIG_FIGS + 1}+ significant figures"
            )
    return issues


def _t1_products(full: str) -> list[str]:
    issues: list[str] = []
    seen: set[tuple[int, int]] = set()
    for m in MULTIPLY_RE.finditer(full):
        a, b = int(m.group(1)), int(m.group(2))
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        if not _is_mental_product(a, b):
            issues.append(
                f"product {a} × {b} has no nice structure — not mental arithmetic"
            )
    return issues


def _t1_non_terminating(full: str) -> list[str]:
    issues: list[str] = []
    for m in DECIMAL_RE.finditer(full):
        num = m.group(1)
        if re.match(r"^(19|20)\d{2}", num):
            continue
        decimals = num.split(".", 1)[1]
        if len(decimals) > MAX_DECIMAL_PLACES:
            issues.append(
                f"non-terminating decimal '{num}' beyond 2 decimal places"
            )
    return issues


def _t1_logs(full: str) -> list[str]:
    issues: list[str] = []
    for m in LOG_RE.finditer(full):
        n = float(m.group(1))
        if not _is_clean_log_arg(n):
            issues.append(
                f"logarithm '{m.group(0).strip()}' is of a non-exact power — "
                f"requires a calculator"
            )
    return issues


def _t1_constants(full: str, stem: str) -> list[str]:
    """Reject named physical constants used in the solution but absent from the stem."""
    issues: list[str] = []
    used = set(m.group(1).lower() for m in PHYSICAL_CONSTANT_NAMES.finditer(full))
    given = set(m.group(1).lower() for m in PHYSICAL_CONSTANT_NAMES.finditer(stem))
    for name in sorted(used - given):
        issues.append(
            f"physical constant '{name}' is used but not provided in the question stem"
        )
    return issues


# ---------------------------------------------------------------------------
# Tier 2 checks (warn only)
# ---------------------------------------------------------------------------

def _t2_roots(full: str) -> list[str]:
    issues: list[str] = []
    for m in SQRT_RE.finditer(full):
        n = float(m.group(1))
        if not _is_clean_root(n):
            issues.append(
                f"non-perfect square root '{m.group(0).strip()}' needs decimal "
                f"precision or simplification (e.g. √50 → 5√2)"
            )
    return issues


def _t2_fractions(full: str) -> list[str]:
    issues: list[str] = []
    for m in FRACTION_RE.finditer(full):
        denom = int(m.group(1))
        if denom > 12:
            issues.append(
                f"fraction with denominator {denom} (> 12) is awkward mental arithmetic"
            )
    return issues


def _t2_non_si_units(full: str) -> list[str]:
    return [
        f"non-SI unit '{m.group(0).strip()}' requires a conversion factor"
        for m in NON_SI_UNITS.finditer(full)
    ]


def _t2_slash_units(full: str) -> list[str]:
    return [
        f"compound unit '{m.group(0).strip()}' uses a slash — prefer negative indices (e.g. m s⁻¹)"
        for m in SLASH_UNIT_RE.finditer(full)
    ]


TIER1_CHECKS = (
    _t1_g_value,
    _t1_trig_angles,
    _t1_sig_figs,
    _t1_products,
    _t1_non_terminating,
    _t1_logs,
    _t1_constants,
)

TIER2_CHECKS = (
    _t2_roots,
    _t2_fractions,
    _t2_non_si_units,
    _t2_slash_units,
)


# ---------------------------------------------------------------------------
# Core gate
# ---------------------------------------------------------------------------

def check(question: dict[str, Any]) -> dict[str, Any]:
    """Run the calculability checker against a single question.

    Accepts the corpus schema:
        {question_text, options, worked_solution|explanation, has_diagram, ...}
    """
    full = _flatten(question)
    stem = _stem(question)
    correct_path = _correct_path(question)
    has_diagram = _has_diagram(question)

    tier1: list[str] = []
    for fn in TIER1_CHECKS:
        try:
            if fn is _t1_g_value:
                tier1.extend(fn(stem))  # ESA-55: g-assignment lives in the stem
            elif fn is _t1_trig_angles:
                tier1.extend(fn(full, has_diagram))
            elif fn is _t1_constants:
                tier1.extend(fn(full, stem))
            elif fn in (_t1_sig_figs, _t1_non_terminating):
                # ESA-55: decimal/sig-fig checks scan the correct-answer path
                # only — distractor options carry deliberately wrong values.
                tier1.extend(fn(correct_path))
            else:
                tier1.extend(fn(full))
        except Exception as exc:  # never let one rule crash the whole gate
            tier1.append(f"[calculability internal error in {fn.__name__}: {exc}]")

    tier2: list[str] = []
    for fn in TIER2_CHECKS:
        try:
            tier2.extend(fn(full))
        except Exception as exc:
            tier2.append(f"[calculability internal error in {fn.__name__}: {exc}]")

    if tier1:
        return verdict(
            passed=False,
            score=0.0,
            reason=f"{len(tier1)} Tier-1 (reject) calculability issue(s)"
                   + (f", {len(tier2)} Tier-2 warning(s)" if tier2 else ""),
            issues=tier1 + tier2,
            cost_usd=0.0,
            gate="calculability",
            tier1=tier1,
            tier2=tier2,
        )

    if tier2:
        return verdict(
            passed=True,
            score=0.5,
            reason=f"{len(tier2)} Tier-2 calculability warning(s) (accepted)",
            issues=tier2,
            cost_usd=0.0,
            gate="calculability",
            tier1=[],
            tier2=tier2,
        )

    return verdict(
        passed=True,
        score=1.0,
        reason="all arithmetic is calculator-free",
        issues=[],
        cost_usd=0.0,
        gate="calculability",
        tier1=[],
        tier2=[],
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

SELF_TEST_CASES: list[tuple[str, dict[str, Any], bool]] = [
    ("clean_integer_arithmetic",
     {"question_text": "A 2 kg mass is accelerated at 3 m/s^2. Find the force.",
      "options": {"A": "6 N"}, "worked_solution": "F = ma = 2 × 3 = 6 N"}, True),
    ("g_equals_ten_ok",
     {"question_text": "A 2 kg object falls. Use g = 10.",
      "options": {"A": "20 N"}, "worked_solution": "F = mg = 2 × 10 = 20 N"}, True),
    ("g_in_division_not_false_reject",
     {"question_text": "A block has volume 40 cm³ and weight 4.0 N. "
                       "(Take g = 10 N kg⁻¹) Find the density in g cm⁻³.",
      "options": {"A": "10"},
      "worked_solution": "m = W/g = 4.0/10 = 0.4 kg = 400 g; ρ = m/V = 400/40 = 10 g cm⁻³"},
     True),
    ("standard_trig_ok",
     {"question_text": "Find sin(30°).",
      "options": {"A": "0.5"}, "worked_solution": "sin(30°) = 1/2"}, True),
    ("nice_product_ok",
     {"question_text": "Compute 16 × 25.",
      "options": {"A": "400"}, "worked_solution": "16 × 25 = 400"}, True),
    ("log_exact_power_ok",
     {"question_text": "Compute log(1000).",
      "options": {"A": "3"}, "worked_solution": "log(1000) = 3"}, True),
    ("g_not_ten_reject",
     {"question_text": "A 2 kg mass falls. Find the weight.",
      "options": {"A": "19.62 N"}, "worked_solution": "W = mg = 2 × 9.81 = 19.62 N"}, False),
    ("nonstandard_angle_reject",
     {"question_text": "Find sin(37°).",
      "options": {"A": "0.60"}, "worked_solution": "sin(37°) ≈ 0.602"}, False),
    ("ugly_product_reject",
     {"question_text": "Compute 17 × 23.",
      "options": {"A": "391"}, "worked_solution": "17 × 23 = 391"}, False),
    ("too_many_sig_figs_reject",
     {"question_text": "What is the result?",
      "options": {"A": "4.1231"}, "worked_solution": "= 4.1231"}, False),
    ("bad_log_reject",
     {"question_text": "Compute log(7).",
      "options": {"A": "0.845"}, "worked_solution": "log(7) ≈ 0.845"}, False),
    ("constant_not_given_reject",
     {"question_text": "A gas is heated. Find the energy.",
      "options": {"A": "5 J"},
      "worked_solution": "E = (3/2) k_B T using the Boltzmann constant"}, False),
    ("constant_given_in_stem_ok",
     {"question_text": "Using the Boltzmann constant k_B = 1.38e-23, find the energy.",
      "options": {"A": "5 J"},
      "worked_solution": "E = (3/2) k_B T with the Boltzmann constant"}, True),
    ("warn_ugly_root_accepts",
     {"question_text": "Simplify the magnitude.",
      "options": {"A": "7.07"}, "worked_solution": "√50 ≈ 7.07"}, True),
    ("warn_high_denominator_accepts",
     {"question_text": "Evaluate the fraction.",
      "options": {"A": "0.23"}, "worked_solution": "3/13 = 0.23"}, True),
    # ESA-55: the "Why the other options are wrong" rationale deliberately
    # contains wrong values that must NOT be scanned.
    ("distractor_rationale_wrong_g_not_reject",
     {"question_text": "A block has weight 40 N and dimensions 4×5×4 cm. "
                       "(Take g = 10 N kg⁻¹.) Find the density in g/cm³.",
      "options": {"A": "50", "B": "0.05", "C": "5", "D": "500", "E": "0.5"},
      "correct_answer": "A",
      "explanation": "m = W/g = 40/10 = 4 kg = 4000 g; V = 4×5×4 = 80 cm³; "
                     "ρ = 4000/80 = 50 g cm⁻³. This is option A.\n\n"
                     "**Why the other options are wrong:**\n"
                     "  - **D**: Incorrectly divided by g = 0.1 instead of "
                     "g = 10, inflating the mass to 40000 g."},
     True),
    # ESA-55: a distractor option may carry an extreme (deliberately wrong)
    # decimal value; the correct path is clean so the question is accepted.
    ("distractor_option_extreme_decimal_not_reject",
     {"question_text": "Convert an area of 5 m² to cm².",
      "options": {"A": "50000 cm²", "B": "0.00005 cm²", "C": "5 cm²"},
      "correct_answer": "A",
      "worked_solution": "5 m² × 10000 = 50000 cm²"},
     True),
]


def _run_self_test() -> int:
    failures = 0
    for name, q, expected in SELF_TEST_CASES:
        result = check(q)
        ok = result["pass"] == expected
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {name}: pass={result['pass']} expected={expected}")
        if not ok:
            for issue in result.get("tier1", []) or result["issues"]:
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
    if isinstance(data, dict) and "questions" in data and isinstance(data["questions"], list):
        return data["questions"][0]
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT calculability checker (Layer 1)")
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
