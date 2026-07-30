#!/usr/bin/env python3
"""
SymPy Solution Verifier — Layer 2 of the verification stack (ESA-45).

For maths/physics questions whose worked solution contains a solvable
equation, this gate:

1. Extracts mathematical expressions from the question + worked solution.
2. Solves the equation symbolically for the unknown.
3. Compares the SymPy result to the **stated correct answer option**.
   - matches the correct option  → **pass**
   - matches a *different* option → **reject**
4. If the question is graphical, conceptual, or has no extractable equation,
   the gate **skips** (pass with score 0.5) — never a false reject.

This is deliberately conservative: it only rejects when SymPy can *positively*
show that solving the equation lands on a wrong option. Everything ambiguous
is left to the downstream LLM solver / reviewer gates.

Parsing is hard, so this module **reuses the battle-tested LaTeX-stripping and
equation-extraction helpers** from the legacy `sympy_verifier.py` rather than
duplicating them. The difference vs. that module: sympy_verifier checks
*internal equation consistency* (lhs == rhs); this module *solves* the equation
and compares the answer to the marked option.

Standard verdict dict:

    {
        "pass": bool,          # True unless a wrong option is provably matched
        "score": float,        # 1.0 verified / 0.5 unsolvable / 0.0 contradicted
        "reason": str,
        "issues": list[str],
        "cost_usd": 0.0,
        "gate": "sympy_verify",
    }

Usage:
    python sympy_verify.py --question path/to/q.json
    python sympy_verify.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
    from sympy_verifier import (  # type: ignore
        _strip_latex,
        _extract_math_regions,
        _extract_equations,
        _safe_sympify,
    )
else:
    from .verdict import verdict  # type: ignore
    from .sympy_verifier import (  # type: ignore
        _strip_latex,
        _extract_math_regions,
        _extract_equations,
        _safe_sympify,
    )

try:
    import sympy  # type: ignore
except ImportError:  # pragma: no cover
    sympy = None  # type: ignore


# Symbol names we treat as known constants (not the unknown to solve for).
KNOWN_CONSTANTS = {"pi", "E", "I", "oo", "g"}
# Numeric value substitutions for common physical constants before solving.
CONSTANT_SUBS = {"g": 10}

# English prose tokens — if an equation side contains any of these as a whole
# word, it is prose (e.g. "8 and x", "the answer is"), not a real expression.
# Rejecting these avoids sympy accidentally parsing "8 and x" → Symbol('x'),
# which is fragile and depends on sympy's global cache state.
PROSE_WORD_RE = re.compile(
    r"\b(and|or|so|the|a|an|is|are|be|of|to|in|for|if|then|when|than|what|"
    r"which|with|where|that|this|hence|thus|since|because|let|find|solve|"
    r"answer|option|value|given|using|we|from|into|each|both|not|no)\b",
    re.IGNORECASE,
)


def _unsolvable(reason: str, issues: Optional[list[str]] = None) -> dict[str, Any]:
    return verdict(
        passed=True,
        score=0.5,
        reason=reason,
        issues=issues or [],
        cost_usd=0.0,
        gate="sympy_verify",
    )


# ---------------------------------------------------------------------------
# Option handling
# ---------------------------------------------------------------------------

_LEADING_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:\s*[×x*]\s*10\^?(-?\d+))?")


def _options_map(question: dict[str, Any]) -> dict[str, str]:
    opts = question.get("options")
    if isinstance(opts, dict):
        return {str(k).upper(): str(v) for k, v in opts.items()}
    if isinstance(opts, list):
        letters = "ABCDEFGHI"
        return {letters[i]: str(v) for i, v in enumerate(opts) if i < len(letters)}
    return {}


def _option_number(text: str) -> Optional[float]:
    """Extract the leading numeric value from an option string.

    Handles '4', '4.0 m/s', '2 × 10^3', '-3.5', '1/2'. Returns None when the
    option is purely conceptual (no leading number).
    """
    t = text.strip()
    # Plain fraction a/b.
    m = re.match(r"^\s*(\d+)\s*/\s*(\d+)\b", t)
    if m:
        return float(m.group(1)) / float(m.group(2))
    m = _LEADING_NUMBER_RE.match(t)
    if not m:
        return None
    try:
        val = float(m.group(0))
    except ValueError:
        return None
    return val


# ---------------------------------------------------------------------------
# Solving
# ---------------------------------------------------------------------------

def _solve_equation(lhs_str: str, rhs_str: str) -> Optional[list[sympy.Expr]]:
    """Solve lhs = rhs for its single unknown; return concrete solutions.

    Returns None if there is not exactly one unknown or SymPy cannot solve it.
    Only fully-numeric solutions are returned.
    """
    if sympy is None:
        return None
    lhs = _safe_sympify(lhs_str)
    rhs = _safe_sympify(rhs_str)
    if lhs is None or rhs is None:
        return None

    expr = lhs - rhs
    try:
        expr = expr.subs([(sympy.Symbol(k), v) for k, v in CONSTANT_SUBS.items()])
    except Exception:
        pass

    free = {s for s in expr.free_symbols if s.name not in KNOWN_CONSTANTS}
    if len(free) != 1:
        return None
    sym = next(iter(free))

    # If already a concrete number, it's not really an equation in an unknown.
    try:
        if expr.is_number:
            return None
    except Exception:
        pass

    try:
        sols = sympy.solve(expr, sym)
    except (NotImplementedError, ValueError, TypeError):
        return None

    concrete: list[sympy.Expr] = []
    for s in sols:
        try:
            if s.is_number and s.is_real:
                concrete.append(s)
        except Exception:
            continue
    return concrete or None


def _value_matches(value: float, target: float, *, rel_tol: float = 0.02, abs_tol: float = 0.01) -> bool:
    if target == 0:
        return abs(value) < abs_tol
    return abs(value - target) <= max(abs_tol, rel_tol * abs(target))


def _is_prose_side(side: str) -> bool:
    """True if an equation side reads as English prose rather than an expression.

    Rejects sides like "8 and x" or "the speed is" so we never rely on sympy
    accidentally coercing prose into a Symbol (which is cache-state dependent).
    Single-letter variables (v, x, F) are NOT prose and must pass through.
    """
    s = side.strip().strip(".,;:").strip()
    if not s:
        return True
    if PROSE_WORD_RE.search(s):
        return True
    return False


def _gather_equations(sources: list[str]) -> list[tuple[str, str]]:
    """Extract clean (lhs, rhs) equations, dropping prose-contaminated sides."""
    out: list[tuple[str, str]] = []
    for src in sources:
        if not src.strip():
            continue
        for region in _extract_math_regions(src):
            for lhs, rhs in _extract_equations(_strip_latex(region)):
                if _is_prose_side(lhs) or _is_prose_side(rhs):
                    continue
                out.append((lhs, rhs))
    return out


# ---------------------------------------------------------------------------
# Core gate
# ---------------------------------------------------------------------------

def check(question: dict[str, Any]) -> dict[str, Any]:
    if sympy is None:
        return _unsolvable("sympy unavailable — gate skipped", ["sympy not installed"])

    correct_answer = str(question.get("correct_answer", "")).strip().upper()
    options = _options_map(question)
    if not re.fullmatch(r"[A-I]", correct_answer) or correct_answer not in options:
        # No ground-truth option to compare against.
        return _unsolvable("no marked correct option — gate skipped")

    # Gather candidate equations from BOTH the question stem and the solution.
    sources = [
        str(question.get("question_text", "")),
        str(question.get("worked_solution", "") or question.get("explanation", "")),
    ]
    equations = _gather_equations(sources)

    if not equations:
        return _unsolvable("unsolvable — no equation found in question or solution")

    # Numeric value of the marked-correct option (if any).
    correct_value = _option_number(options[correct_answer])

    issues: list[str] = []
    verified = False
    contradicted = False

    for lhs, rhs in equations:
        sols = _solve_equation(lhs, rhs)
        if not sols:
            continue
        for sol in sols:
            try:
                val = float(sol)
            except (TypeError, ValueError):
                continue

            # Which option does this solved value land on?
            matched_letter: Optional[str] = None
            for letter, text in options.items():
                oval = _option_number(text)
                if oval is None:
                    continue
                if _value_matches(val, oval):
                    matched_letter = letter
                    break

            if matched_letter is None:
                issues.append(f"solved {val:g} from '{lhs}={rhs}' matches no option")
                continue

            if matched_letter == correct_answer:
                verified = True
                issues.append(f"solved {val:g} matches correct option {correct_answer}")
            else:
                # Positive contradiction: the equation's solution is a WRONG option.
                contradicted = True
                issues.append(
                    f"solved {val:g} from '{lhs}={rhs}' matches option {matched_letter}, "
                    f"not marked-correct {correct_answer}"
                )

    if contradicted:
        return verdict(
            passed=False,
            score=0.0,
            reason="symPy solved answer disagrees with the marked correct option",
            issues=issues,
            cost_usd=0.0,
            gate="sympy_verify",
        )

    if verified:
        return verdict(
            passed=True,
            score=1.0,
            reason="symPy solution matches the marked correct option",
            issues=issues,
            cost_usd=0.0,
            gate="sympy_verify",
        )

    return _unsolvable("unsolvable — SymPy could not map a solution to an option", issues)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

SELF_TEST_CASES = [
    (
        "verified_linear_numeric",
        {
            "question_text": "Solve for x: $2x + 3 = 11$.",
            "options": {"A": "2", "B": "3", "C": "4", "D": "5"},
            "correct_answer": "C",
            "explanation": "$2x + 3 = 11$ so $x = 4$.",
        },
        True,
    ),
    (
        "contradicted_wrong_option",
        {
            "question_text": "Solve for x: $2x + 3 = 11$.",
            "options": {"A": "2", "B": "3", "C": "4", "D": "5"},
            "correct_answer": "B",
            "explanation": "$2x + 3 = 11$ so $x = 4$.",
        },
        False,
    ),
    (
        "conceptual_unsolvable",
        {
            "question_text": "Which organelle is the site of aerobic respiration?",
            "options": {"A": "Nucleus", "B": "Mitochondrion", "C": "Ribosome", "D": "Vacuole"},
            "correct_answer": "B",
            "explanation": "Aerobic respiration occurs in the mitochondrion.",
        },
        True,
    ),
    (
        "no_equation_unsolvable",
        {
            "question_text": "Describe the trend in reactivity down Group 1.",
            "options": {"A": "increases", "B": "decreases", "C": "no change", "D": "oscillates"},
            "correct_answer": "A",
            "explanation": "Reactivity increases down the group.",
        },
        True,
    ),
    (
        "verified_with_units",
        {
            "question_text": "A body starts from rest. Find $v$ given $v = 2 \\times 3$.",
            "options": {"A": "5 m/s", "B": "6 m/s", "C": "9 m/s", "D": "1.5 m/s"},
            "correct_answer": "B",
            "explanation": "$v = 2 \\times 3 = 6$ m/s.",
        },
        True,
    ),
]


def _run_self_test() -> int:
    failures = 0
    for name, q, expected in SELF_TEST_CASES:
        result = check(q)
        ok = result["pass"] == expected
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {name}: pass={result['pass']} score={result['score']}")
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
    if isinstance(data, dict) and "questions" in data and isinstance(data["questions"], list):
        return data["questions"][0]
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT SymPy solution verifier (Layer 2)")
    p.add_argument("--question", type=Path, help="Path to a question JSON file")
    p.add_argument("--self-test", action="store_true", help="Run built-in test cases")
    args = p.parse_args(argv)

    if args.self_test:
        return _run_self_test()

    if not args.question:
        p.error("--question or --self-test is required")

    question = _load_question(args.question)
    print(json.dumps(check(question), indent=2))
    return 0 if check(question)["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
