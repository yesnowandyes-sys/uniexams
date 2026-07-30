#!/usr/bin/env python3
"""
SymPy Symbolic Verifier (Gate 2 of the 4-gate stack).

Provides symbolic ground-truth verification for Maths and Physics questions
where the worked solution can be expressed algebraically. Per
`orchestration-review.md` §7, SymPy covers ~40–50% of Maths/Physics —
**when this gate cannot verify, it returns `'unsolvable'`, NOT a fail.**
A fail is reserved for cases where SymPy can positively show the worked
solution is wrong.

Strategy
--------
1. Parse the worked solution looking for an equation of the form
   `lhs = rhs` (or `answer = value`).
2. Try SymPy `simplify(lhs - rhs) == 0`.
3. For algebraic identities, attempt `sympy.Eq(lhs, rhs).simplify()`.
4. If no equation can be parsed, return `score=0.0, reason='unsolvable'`.

This module is deliberately conservative — it only fails a question when it
can prove the worked solution is inconsistent. For everything else, it lets
the downstream LLM solver / reviewer gates decide.

Standard verdict dict:

    {
        "pass": bool,           # True if verified OR unsolvable
        "score": float,         # 1.0 verified, 0.5 unsolvable, 0.0 contradicted
        "reason": str,
        "issues": list[str],
        "cost_usd": 0.0,
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
else:
    from .verdict import verdict  # type: ignore

try:
    import sympy  # type: ignore
except ImportError:  # pragma: no cover - sympy is a hard dep for this gate
    sympy = None  # type: ignore


# A flexible equation splitter: "a = b", "a == b", "a → b", "a => b".
# Both LHS and RHS exclude `=`, `>`, `→`, `;` so chains like
# `a = b = c = d` produce three separate candidate pairs instead of one
# blob with embedded `=` signs that SymPy cannot parse.
EQUATION_RE = re.compile(
    r"([^\n=>→;]+?)\s*(?:==|=>|→|=)\s*([^\n=>→;]+)"
)

# Inline/display math delimiters: $...$, $$...$$, \(...\), \[...\].
MATH_REGION_RE = re.compile(
    r"\$\$(.+?)\$\$"           # $$...$$
    r"|\$([^$]+)\$"            # $...$
    r"|\\\((.+?)\\\)"          # \(...\)
    r"|\\\[(.+?)\\\]",         # \[...\]
    re.DOTALL,
)

# A unit/label inside \text{...}, \mathrm{...}, \textbf{...}, etc.
# These wrap units (m, s, kg) and prose labels — strip the whole block.
# Also consumes a trailing `^{...}` or `_{...}` so `\text{ m s}^{-1}` is
# stripped in full (unit + unit-exponent together).
# Nested-brace tolerant.
TEXT_BLOCK_RE = re.compile(
    r"\\(?:text|mathrm|textbf|textit|mathbf|mathit|operatorname)"
    r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    r"(?:\s*\^\{[^{}]*\}|\s*_\{[^{}]*\})?"
)

# Commands we translate to a SymPy-friendly name (Greek letters, funcs).
LATEX_TRANSLATIONS: dict[str, str] = {
    # Greek letters (lowercase).
    r"\alpha": "alpha", r"\beta": "beta", r"\gamma": "gamma",
    r"\delta": "delta", r"\epsilon": "epsilon", r"\zeta": "zeta",
    r"\eta": "eta", r"\theta": "theta", r"\iota": "iota",
    r"\kappa": "kappa", r"\lambda": "_lambda", r"\mu": "mu",
    r"\nu": "nu", r"\xi": "xi", r"\pi": "pi", r"\rho": "rho",
    r"\sigma": "sigma", r"\tau": "tau", r"\phi": "phi",
    r"\chi": "chi", r"\psi": "psi", r"\omega": "omega",
    # Functions.
    r"\sin": "sin", r"\cos": "cos", r"\tan": "tan",
    r"\cot": "cot", r"\sec": "sec", r"\csc": "csc",
    r"\arcsin": "asin", r"\arccos": "acos", r"\arctan": "atan",
    r"\sinh": "sinh", r"\cosh": "cosh", r"\tanh": "tanh",
    r"\ln": "ln", r"\log": "log", r"\exp": "exp",
    r"\sqrt": "sqrt", r"\abs": "Abs", r"\det": "det",
    # Operators.
    r"\cdot": "*", r"\times": "*", r"\div": "/",
    r"\pm": " ", r"\mp": " ",
    # Constants.
    r"\infty": "oo",
}

# Braced-argument commands that take exactly one argument we want to drop.
# (\circ, \deg, \prime, \dprime, etc. — drop entirely.)
LATEX_DROP_BRACED_RE = re.compile(
    r"\\(?:circ|deg|prime|dprime|displaystyle|scriptstyle|,|;|!|:|quad|qquad)"
)

# Angle/degree markers that should be dropped (after handling ^\circ etc.).
LATEX_CIRC_RE = re.compile(r"\\circ\b")
DEGREE_CHARS = "°∘′″"


def _match_balanced_braces(text: str, start: int) -> tuple[str, int]:
    """Return (content, end_index) for the {...} group starting at `start`.

    `start` is the index of the opening brace. Handles nested braces.
    Returns ("", start) if `text[start]` is not `{`.
    """
    if start >= len(text) or text[start] != "{":
        return "", start
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i
        elif c == "\\" and i + 1 < len(text):
            # Skip the next char after a backslash so `\{` doesn't confuse depth.
            i += 1
    # Unbalanced — return what we have.
    return text[start + 1:], len(text) - 1


def _expand_frac(text: str) -> str:
    """Expand ``\\frac{a}{b}`` → ``(a)/(b)`` with brace-balanced parsing.

    Handles nested fractions like ``\\frac{1}{\\frac{1}{2}}``.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith(r"\frac", i):
            j = i + len(r"\frac")
            # Skip whitespace.
            while j < len(text) and text[j].isspace():
                j += 1
            if j >= len(text) or text[j] != "{":
                # Malformed \frac — drop the command and continue.
                i = j
                continue
            num, after_num = _match_balanced_braces(text, j)
            k = after_num + 1
            while k < len(text) and text[k].isspace():
                k += 1
            if k >= len(text) or text[k] != "{":
                # No denominator — emit numerator only.
                out.append(f"({_expand_frac(num)})")
                i = k
                continue
            den, after_den = _match_balanced_braces(text, k)
            # Recursively expand nested \frac inside numerator/denominator.
            out.append(f"({_expand_frac(num)})/({_expand_frac(den)})")
            i = after_den + 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _strip_latex(text: str) -> str:
    """Aggressively normalise LaTeX math syntax to a SymPy-parseable string.

    Strategy
    --------
    1. Drop ``\\text{...}`` / ``\\mathrm{...}`` blocks entirely (units, labels).
    2. Expand ``\\frac{a}{b}`` → ``(a)/(b)`` (brace-balanced, nestable).
    3. Translate known commands (Greek letters, trig, log) to plain names.
    4. Drop angle/degree markers (``\\circ``, ``°``) — they are metadata,
       not numerical content.
    5. Strip residual unknown ``\\cmd`` backslash-commands.
    6. Convert braces to parentheses so SymPy parses grouped expressions.
    7. Convert ``^`` → ``**`` for exponentiation (ESAT convention).
    """
    # 1. Strip \text{...}, \mathrm{...}, etc. — these carry units/labels.
    text = TEXT_BLOCK_RE.sub(" ", text)

    # 2. Expand \frac{a}{b} → (a)/(b) before brace conversion.
    text = _expand_frac(text)

    # 3. Translate named commands with their SymPy equivalents.
    for cmd, repl in LATEX_TRANSLATIONS.items():
        text = text.replace(cmd, repl)

    # 4. Drop degree / angle / spacing markers.
    text = LATEX_CIRC_RE.sub(" ", text)
    text = LATEX_DROP_BRACED_RE.sub(" ", text)
    for ch in DEGREE_CHARS:
        text = text.replace(ch, "")

    # 5. Strip residual backslash-commands we did not translate.
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    # Drop lone backslashes (e.g. leftover `\,`).
    text = re.sub(r"\\[^a-zA-Z]?", " ", text)

    # 6. Braces → parens (keeps grouping; nested braces already work).
    text = text.replace("{", "(").replace("}", ")")

    # 7. ESAT-style: caret is exponent, not XOR (Python's default).
    text = text.replace("^", "**")

    # Collapse whitespace.
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Insert `*` between a digit and a letter so `2x` becomes `2*x`.
IMPLICIT_MULT_DIGIT_LETTER_RE = re.compile(r"(\d)([A-Za-z(])")
# Insert `*` between `)` and a letter/digit, allowing whitespace, so
# `(x-1) (x+1)` → `(x-1)*(x+1)`.
IMPLICIT_MULT_PAREN_RE = re.compile(r"(\))\s*(\()|(\))\s*([A-Za-z])")


def _preprocess_for_sympy(expr: str) -> str:
    """Insert implicit-multiplication operators SymPy won't infer."""
    expr = IMPLICIT_MULT_DIGIT_LETTER_RE.sub(r"\1*\2", expr)
    expr = IMPLICIT_MULT_PAREN_RE.sub(
        lambda m: (m.group(1) + "*" + m.group(2))
        if m.group(1)
        else (m.group(3) + "*" + m.group(4)),
        expr,
    )
    return expr


def _safe_sympify(expr: str) -> sympy.Basic | None:
    if sympy is None:
        return None
    try:
        return sympy.sympify(_preprocess_for_sympy(expr), evaluate=True)
    except (sympy.SympifyError, TypeError, SyntaxError, ValueError):
        return None


def _extract_math_regions(text: str) -> list[str]:
    """Return the contents of every $...$ / $$...$$ / \\(...\\) / \\[...\\] region.

    If the text contains *no* math delimiters at all, return [text] — many
    plain-text worked solutions are valid math without delimiters.
    """
    regions: list[str] = []
    for m in MATH_REGION_RE.finditer(text):
        # Exactly one group will be non-None.
        for g in m.groups():
            if g:
                regions.append(g)
                break
    if not regions:
        # No math delimiters — treat the whole text as one region so we
        # still support plain-text worked solutions like "2x + 3 = 7".
        return [text]
    return regions


def _extract_equations(text: str) -> list[tuple[str, str]]:
    """Return list of (lhs, rhs) candidates from sanitised math text.

    Splits on `=`, `==`, `=>`, `→` and pairs up consecutive chunks so a
    chain like `a = b = c = d` produces three pairs (a,b), (b,c), (c,d)
    rather than dropping everything after the first `=`.

    The strongest filter is SymPy itself: both sides MUST sympify to a
    valid expression.  This naturally rejects prose like "the speed is"
    because it will not parse, while accepting Greek-letter identifiers
    like `_lambda` or `theta`.  We apply a couple of cheap pre-filters
    first to avoid pointless sympify attempts on obvious prose.
    """
    candidates: list[tuple[str, str]] = []
    parts = re.split(r"(?:==|=>|→|=)", text)
    if len(parts) < 2:
        return candidates
    for i in range(len(parts) - 1):
        lhs = parts[i].strip().strip("$").strip()
        rhs = parts[i + 1].strip().strip("$").strip()
        # Skip trivial "answer = E" / "Option = X" mappings.
        if re.fullmatch(r"[A-E]", lhs, re.IGNORECASE) or "option" in lhs.lower():
            continue
        if len(lhs) < 1 or len(rhs) < 1:
            continue
        # Cheap pre-filter: require at least one digit or math operator.
        combined = f"{lhs} {rhs}"
        if not re.search(r"\d|[\+\-\*/\^\(\)\[xyπ]", combined):
            continue
        # Strong filter: both sides must sympify. This drops prose.
        if _safe_sympify(lhs) is None or _safe_sympify(rhs) is None:
            continue
        candidates.append((lhs, rhs))
    return candidates


# ---------------------------------------------------------------------------
# Core verification
# ---------------------------------------------------------------------------

def _verify_equation(lhs_str: str, rhs_str: str) -> tuple[bool, bool, str]:
    """Return (verified, contradicted, reason).

    * verified    → SymPy proves lhs == rhs
    * contradicted → SymPy proves lhs != rhs (a definite numerical mismatch)
    * otherwise   → cannot decide
    """
    if sympy is None:
        return False, False, "sympy not installed"

    lhs = _safe_sympify(lhs_str)
    rhs = _safe_sympify(rhs_str)
    if lhs is None or rhs is None:
        return False, False, f"unparseable: '{lhs_str}' / '{rhs_str}'"

    try:
        diff = sympy.simplify(lhs - rhs)
    except (TypeError, ValueError, ZeroDivisionError):
        return False, False, "simplify raised"

    if diff == 0:
        return True, False, "lhs - rhs == 0"

    # If the difference is a pure number, it's a hard contradiction.
    if diff.is_number:
        return False, True, f"lhs - rhs = {diff} ≠ 0"

    # Could be parameterised — leave for downstream gates.
    return False, False, "symbolic difference remains"


def check(question: dict[str, Any]) -> dict[str, Any]:
    """Verify the worked solution for a single question with SymPy.

    Returns the standard verdict dict. `pass=True` covers BOTH
    "verified" and "unsolvable" — downstream gates (solver, reviewer)
    are responsible for final arbitration.
    """
    if sympy is None:
        return verdict(
            passed=True,
            score=0.5,
            reason="sympy unavailable — gate skipped",
            issues=["sympy not installed"],
            cost_usd=0.0,
            gate="sympy_verifier",
        )

    raw_solution = str(
        question.get("worked_solution", "")
        or question.get("explanation", "")
    )
    if not raw_solution.strip():
        return verdict(
            passed=True,
            score=0.5,
            reason="no worked solution to verify — unsolvable",
            issues=["empty worked solution"],
            cost_usd=0.0,
            gate="sympy_verifier",
        )

    # Only attempt parsing inside $...$ / \(...\) math regions when present.
    # This is the primary defence against prose `=` signs leaking through
    # ("the speed is the relative speed: ...").
    regions = _extract_math_regions(raw_solution)
    equations: list[tuple[str, str]] = []
    for region in regions:
        stripped = _strip_latex(region)
        equations.extend(_extract_equations(stripped))

    if not equations:
        return verdict(
            passed=True,
            score=0.5,
            reason="unsolvable — no equation found in worked solution",
            issues=["no equation parsed"],
            cost_usd=0.0,
            gate="sympy_verifier",
        )

    verified_any = False
    issues: list[str] = []
    contradicted = False

    for lhs, rhs in equations:
        ok, bad, why = _verify_equation(lhs, rhs)
        if ok:
            verified_any = True
        elif bad:
            contradicted = True
            issues.append(f"contradiction: {lhs} != {rhs} ({why})")
        else:
            issues.append(f"undecidable: {lhs} = {rhs} ({why})")

    if contradicted:
        return verdict(
            passed=False,
            score=0.0,
            reason="worked solution contains a symbolic contradiction",
            issues=issues,
            cost_usd=0.0,
            gate="sympy_verifier",
        )

    if verified_any:
        return verdict(
            passed=True,
            score=1.0,
            reason="worked solution verified by SymPy",
            issues=issues,
            cost_usd=0.0,
            gate="sympy_verifier",
        )

    return verdict(
        passed=True,
        score=0.5,
        reason="unsolvable — SymPy could neither verify nor contradict",
        issues=issues,
        cost_usd=0.0,
        gate="sympy_verifier",
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

SELF_TEST_CASES = [
    (
        "verified_identity",
        {"worked_solution": "x^2 - 1 = (x-1)(x+1)"},
        True,
    ),
    (
        "verified_quadratic",
        {"worked_solution": "2x + 3 = 7, so x = 2"},
        True,
    ),
    (
        "contradicted_value",
        {"worked_solution": "2 + 2 = 5"},
        False,
    ),
    (
        "no_equation_unsolvable",
        {"worked_solution": "Consider the function f."},
        True,
    ),
    (
        "empty_solution_unsolvable",
        {"worked_solution": ""},
        True,
    ),
    (
        "parametric_undecidable_unsolvable",
        {"worked_solution": "y = mx + c"},
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT SymPy verifier")
    p.add_argument("--question", type=Path, help="Path to a question JSON file")
    p.add_argument("--self-test", action="store_true", help="Run built-in test cases")
    args = p.parse_args(argv)

    if args.self_test:
        return _run_self_test()

    if not args.question:
        p.error("--question or --self-test is required")

    with args.question.open() as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data:
        data = data["questions"][0]
    print(json.dumps(check(data), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
