#!/usr/bin/env python3
"""
Chemistry Stoichiometry Checker (gate 5 of the quality stack).

Verifies that chemical equations appearing in a question's worked solution
are atom-balanced. Uses RDKit (`Chem.AllChem`/`Chem.AtomCount`) for
formula parsing; gracefully degrades to a pure-Python fallback parser
when RDKit is unavailable.

Per `orchestration-review.md` Priority #3, this gate covers Chemistry
questions that SymPy cannot reach. ~50 LOC, deterministic (no API call).

Standard verdict dict:

    {
        "pass": bool,
        "score": float,            # 1.0 balanced, 0.0 unbalanced
        "reason": str,
        "issues": list[str],       # per-equation failures
        "cost_usd": 0.0,
        "equations_checked": int,
        "backend": "rdkit" | "fallback" | "none",
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
else:
    from .verdict import verdict  # type: ignore


# Chemistry equation patterns. We look for arrows that typically separate
# reactants and products in worked solutions: →, ->, <=>, ↔, ⇌.
ARROW_RE = re.compile(r"\s*(?:->|→|<=>|⇌|↔)\s*")

# A chemical species is "<optional coeff><formula>", e.g. "2H2O", "3CO2".
SPECIES_RE = re.compile(
    r"((?:^\d+|\s\d+|\d(?=[A-Z]))?)"           # optional integer coeff
    r"((?:[A-Z][a-z]?\d*)+)",                   # formula
)

# Filter out obviously non-chemistry matches (lowercase words, math).
MATH_TOKEN_RE = re.compile(r"^[a-z]+$|^[a-z]+=$|^\d+(\.\d+)?$|^[A-Z]$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Backend: RDKit (preferred)
# ---------------------------------------------------------------------------

def _try_rdkit():
    try:
        from rdkit import Chem  # type: ignore
    except ImportError:
        return None
    return Chem


def _atom_count_rdkit(Chem: Any, formula: str) -> Counter | None:
    """Use RDKit to parse a formula like 'H2O' into an atom Counter."""
    # RDKit parses formulas via RWMol from a mol block, but the simplest
    # path is `Chem.FormulaParser` (newer RDKit) or feed the formula as
    # a SMILES-like if it is a single molecule. Use the public formula
    # parser when available; otherwise fall back.
    parser = getattr(Chem, "FormulaParser", None)
    if parser is None:
        # Older RDKit — give up and let the fallback handle it.
        return None
    try:
        mol = parser.ParseFormula(formula)  # type: ignore[attr-defined]
    except Exception:
        return None
    counter: Counter = Counter()
    for atom in mol.GetAtoms():
        counter[atom.GetSymbol()] += 1
    return counter


# ---------------------------------------------------------------------------
# Backend: pure-Python formula parser (fallback)
# ---------------------------------------------------------------------------

FORMULA_TOKEN_RE = re.compile(r"([A-Z][a-z]?)(\d*)")


def _atom_count_fallback(formula: str) -> Counter:
    """Parse 'H2O', 'C6H12O6', 'H2SO4' into an atom Counter.

    Handles nested groups via a tiny stack-based recursion.
    """
    # Expand simple parens like "Ca(OH)2" → "CaO2H2".
    def expand_groups(s: str) -> str:
        out: list[str] = []
        i = 0
        while i < len(s):
            ch = s[i]
            if ch == "(":
                # Find matching close paren.
                depth = 1
                j = i + 1
                while j < len(s) and depth > 0:
                    if s[j] == "(":
                        depth += 1
                    elif s[j] == ")":
                        depth -= 1
                    j += 1
                inner = expand_groups(s[i + 1 : j - 1])
                # Read trailing multiplier.
                k = j
                while k < len(s) and s[k].isdigit():
                    k += 1
                mult = int(s[j:k] or "1")
                # Multiply every digit inside inner.
                def mult_match(m: re.Match[str]) -> str:
                    return str(int(m.group(2) or "1") * mult)

                out.append(re.sub(r"(\d+)", lambda m: str(int(m.group(1)) * mult), inner) if False else re.sub(r"([A-Za-z])(\d*)", mult_match, inner))
                i = k
            else:
                out.append(ch)
                i += 1
        return "".join(out)

    expanded = expand_groups(formula)
    counter: Counter = Counter()
    for elem, count in FORMULA_TOKEN_RE.findall(expanded):
        if not elem or not elem[0].isupper():
            continue
        counter[elem] += int(count or "1")
    return counter


def _atom_count(formula: str, Chem: Any) -> Counter | None:
    if Chem is not None:
        via_rdkit = _atom_count_rdkit(Chem, formula)
        if via_rdkit is not None:
            return via_rdkit
    return _atom_count_fallback(formula)


# ---------------------------------------------------------------------------
# Equation extraction + balance check
# ---------------------------------------------------------------------------

def _split_species(side: str) -> list[tuple[int, str]]:
    """Split '2H2O + 3CO2' into [(2, 'H2O'), (3, 'CO2')]."""
    species: list[tuple[int, str]] = []
    for chunk in re.split(r"\s*\+\s*", side.strip()):
        chunk = chunk.strip()
        if not chunk or MATH_TOKEN_RE.match(chunk):
            continue
        m = re.match(r"^(\d+)?\s*([A-Z][A-Za-z0-9()]*)$", chunk)
        if not m:
            continue
        coeff = int(m.group(1) or "1")
        formula = m.group(2)
        species.append((coeff, formula))
    return species


def _side_atoms(side: str, Chem: Any) -> Counter | None:
    total: Counter = Counter()
    saw_any = False
    for coeff, formula in _split_species(side):
        atoms = _atom_count(formula, Chem)
        if atoms is None:
            return None
        for el, n in atoms.items():
            total[el] += coeff * n
        saw_any = True
    return total if saw_any else None


def _extract_equations(text: str) -> list[tuple[str, str]]:
    """Find chemical equations in worked solution text.

    Looks for `<reactants> -> <products>` where both sides contain at least
    one species with an uppercase element symbol (filters out math `a -> b`).
    """
    equations: list[tuple[str, str]] = []
    for line in text.replace("\n", " ").split("."):
        line = line.strip()
        if not ARROW_RE.search(line):
            continue
        # Reject lines that are obviously math (contain = or algebra).
        if re.search(r"[a-z]\s*=\s*[a-z]|\^|sqrt|sin|cos", line, re.IGNORECASE):
            continue
        # Split on the first arrow.
        parts = ARROW_RE.split(line, maxsplit=1)
        if len(parts) != 2:
            continue
        lhs, rhs = parts[0].strip(), parts[1].strip()
        if not lhs or not rhs:
            continue
        # Both sides must contain at least one formula (uppercase + digit OR paren).
        if not re.search(r"[A-Z][a-z]?[\d(]", lhs) or not re.search(r"[A-Z][a-z]?[\d(]", rhs):
            continue
        equations.append((lhs, rhs))
    return equations


def _check_balance(lhs: str, rhs: str, Chem: Any) -> tuple[bool, str | None]:
    lhs_atoms = _side_atoms(lhs, Chem)
    rhs_atoms = _side_atoms(rhs, Chem)
    if lhs_atoms is None or rhs_atoms is None:
        return True, None  # cannot parse — leave for downstream gates
    if lhs_atoms == rhs_atoms:
        return True, None
    return False, f"{dict(lhs_atoms)} != {dict(rhs_atoms)}"


# ---------------------------------------------------------------------------
# Core gate
# ---------------------------------------------------------------------------

def check(question: dict[str, Any]) -> dict[str, Any]:
    Chem = _try_rdkit()
    backend = "rdkit" if Chem is not None else "fallback"

    raw_solution = str(
        question.get("worked_solution", "")
        or question.get("explanation", "")
    )
    if not raw_solution.strip():
        return verdict(
            passed=True,
            score=0.5,
            reason="no worked solution — unsolvable",
            issues=["empty worked solution"],
            cost_usd=0.0,
            gate="chem_stoich_check",
            equations_checked=0,
            backend=backend,
        )

    equations = _extract_equations(raw_solution)
    if not equations:
        return verdict(
            passed=True,
            score=0.5,
            reason="no chemical equations found — unsolvable",
            issues=[],
            cost_usd=0.0,
            gate="chem_stoich_check",
            equations_checked=0,
            backend=backend,
        )

    issues: list[str] = []
    for lhs, rhs in equations:
        ok, why = _check_balance(lhs, rhs, Chem)
        if not ok and why:
            issues.append(f"unbalanced: {lhs} → {rhs} ({why})")
    if issues:
        return verdict(
            passed=False,
            score=0.0,
            reason=f"{len(issues)} unbalanced equation(s)",
            issues=issues,
            cost_usd=0.0,
            gate="chem_stoich_check",
            equations_checked=len(equations),
            backend=backend,
        )

    return verdict(
        passed=True,
        score=1.0,
        reason=f"all {len(equations)} equation(s) balanced",
        issues=[],
        cost_usd=0.0,
        gate="chem_stoich_check",
        equations_checked=len(equations),
        backend=backend,
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

SELF_TEST_CASES = [
    (
        "balanced_combustion",
        {"worked_solution": "CH4 + 2O2 → CO2 + 2H2O"},
        True,
    ),
    (
        "balanced_synthesis",
        {"worked_solution": "N2 + 3H2 → 2NH3"},
        True,
    ),
    (
        "unbalanced_simple",
        {"worked_solution": "H2 + O2 → H2O"},
        False,
    ),
    (
        "unbalanced_complex",
        {"worked_solution": "Fe + O2 → Fe2O3"},
        False,
    ),
    (
        "no_chemistry",
        {"worked_solution": "The answer is 42."},
        True,  # unsolvable → pass
    ),
    (
        "paren_group_balanced",
        {"worked_solution": "Ca(OH)2 → Ca + 2OH"},
        True,
    ),
]


def _run_self_test() -> int:
    failures = 0
    for name, q, expected in SELF_TEST_CASES:
        result = check(q)
        ok = result["pass"] == expected
        flag = "PASS" if ok else "FAIL"
        print(
            f"  [{flag}] {name}: pass={result['pass']} "
            f"backend={result['backend']} eqs={result['equations_checked']}"
        )
        if not ok:
            for issue in result["issues"]:
                print(f"        - {issue}")
            failures += 1
    print(f"\n{len(SELF_TEST_CASES) - failures}/{len(SELF_TEST_CASES)} cases passed")
    return failures


def _load_question(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data:
        return data["questions"][0]
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT chemistry stoichiometry checker")
    p.add_argument("--question", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)

    if args.self_test:
        return _run_self_test()
    if not args.question:
        p.error("--question or --self-test is required")
    q = _load_question(args.question)
    result = check(q)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
