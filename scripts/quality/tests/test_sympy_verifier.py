"""Tests for the SymPy symbolic verifier (Gate 2)."""

from __future__ import annotations

import sympy_verifier as sv  # type: ignore


def test_verified_identity_scores_high():
    result = sv.check({"worked_solution": "x^2 - 1 = (x-1)(x+1)"})
    assert result["pass"]
    assert result["score"] >= 0.5  # verified OR unsolvable both pass


def test_contradicted_value_fails():
    result = sv.check({"worked_solution": "2 + 2 = 5"})
    assert not result["pass"]
    assert result["score"] == 0.0
    assert result["reason"] == "worked solution contains a symbolic contradiction"


def test_empty_solution_unsolvable_passes():
    result = sv.check({"worked_solution": ""})
    assert result["pass"]
    assert result["score"] == 0.5


def test_no_equation_unsolvable_passes():
    result = sv.check({"worked_solution": "Consider the function f."})
    assert result["pass"]
    assert result["reason"].startswith("unsolvable")


def test_parametric_undecidable_unsolvable():
    result = sv.check({"worked_solution": "y = mx + c"})
    assert result["pass"]
    assert result["score"] == 0.5


def test_prose_not_treated_as_equation():
    """Yellow + yellow = yellow should NOT be parsed as a contradiction."""
    result = sv.check({"worked_solution": "yellow + yellow = yellow"})
    assert result["pass"]


# ---------------------------------------------------------------------------
# LaTeX handling regressions (ESA-38).
# ---------------------------------------------------------------------------

def test_latex_text_block_units_stripped():
    """`\\text{ m s}^{-1}` is a unit — must not leak `^{-1}` as an exponent."""
    result = sv.check({
        "worked_solution": r"$v = 4 + 10 = 14 \text{ m s}^{-1}$"
    })
    assert result["pass"]
    assert result["score"] == 1.0, f"expected verified, got {result}"


def test_latex_nested_fractions_verified():
    """`\\frac{1}{2} + \\frac{1}{2} = 1` should verify."""
    result = sv.check({
        "worked_solution": r"$\frac{1}{2} + \frac{1}{2} = 1$"
    })
    assert result["pass"]
    assert result["score"] == 1.0


def test_latex_doubly_nested_fraction_verified():
    """`\\frac{1}{\\frac{1}{2}} = 2` requires recursive fraction expansion."""
    result = sv.check({
        "worked_solution": r"$\frac{1}{\frac{1}{2}} = 2$"
    })
    assert result["pass"]
    assert result["score"] == 1.0


def test_latex_left_right_parens_verified():
    """`\\left(x+1\\right)\\left(x-1\\right) = x^2 - 1` should verify."""
    result = sv.check({
        "worked_solution": r"$\left(x+1\right)\left(x-1\right) = x^2 - 1$"
    })
    assert result["pass"]
    assert result["score"] == 1.0


def test_latex_greek_and_trig_verified():
    """`\\sin(\\pi/2) = 1` requires Greek+trig translation."""
    result = sv.check({
        "worked_solution": r"$\sin(\pi/2) = 1$"
    })
    assert result["pass"]
    assert result["score"] == 1.0


def test_latex_chain_of_equals_verified():
    """`5 + 3 = 8 = 4 \\times 2` — chained `=` must split into pairs."""
    result = sv.check({
        "worked_solution": r"$5 + 3 = 8 = 4 \times 2$"
    })
    assert result["pass"]
    assert result["score"] == 1.0


def test_latex_sqrt_verified():
    result = sv.check({"worked_solution": r"$\sqrt{9} = 3$"})
    assert result["pass"]
    assert result["score"] == 1.0


def test_latex_contradiction_inside_math_region_detected():
    """A real contradiction inside `$...$` must still be flagged."""
    result = sv.check({"worked_solution": r"The answer is $2 + 2 = 5$"})
    assert not result["pass"]
    assert result["score"] == 0.0


def test_latex_prose_outside_math_region_ignored():
    """Prose `=` outside `$...$` regions must not be parsed as equations."""
    result = sv.check({
        "worked_solution":
            r"Because the speed is the relative speed: $d = 5 \times 2 = 10$."
    })
    # The math region `d = 5 * 2 = 10` should verify (10 = 10).
    assert result["pass"]
    assert result["score"] == 1.0


def test_latex_text_block_with_label_stripped():
    """`\\text{rel}` inside subscript should not leave a stray identifier."""
    result = sv.check({
        "worked_solution":
            r"$v_{\text{rel}} = v_{\text{wave}} + v_{\text{ship}} = 4 + 10 = 14$"
    })
    # `4 + 10 = 14` should verify; the v_{} candidates become undecidable
    # but not contradicted.
    assert result["pass"]
    assert result["score"] == 1.0


def test_latex_degree_marker_dropped():
    """`90^\\circ` — degree marker must not break parsing."""
    result = sv.check({
        "worked_solution": r"In $T$, $\angle X = 90^\circ$ and $y = 7$"
    })
    # `y = 7` is parametric so undecidable; the gate should still pass.
    assert result["pass"]

