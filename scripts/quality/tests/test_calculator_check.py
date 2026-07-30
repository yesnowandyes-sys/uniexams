"""Tests for the calculator-free arithmetic checker (Gate 1)."""

from __future__ import annotations

import calculator_check as cc  # type: ignore


# ---------------------------------------------------------------------------
# Verdict-shape contract
# ---------------------------------------------------------------------------

def test_verdict_dict_shape(sample_maths_question):
    result = cc.check(sample_maths_question)
    assert set(result) >= {"pass", "score", "reason", "issues", "cost_usd"}
    assert isinstance(result["pass"], bool)
    assert 0.0 <= result["score"] <= 1.0
    assert result["cost_usd"] == 0.0


# ---------------------------------------------------------------------------
# Pass cases (one per rule branch)
# ---------------------------------------------------------------------------

PASS_CASES = [
    ("perfect_square_root", {"question_text": "Simplify √81.", "options": {"A": "9"}, "worked_solution": "9 × 9 = 81"}),
    ("common_surd_answer", {"question_text": "Find the magnitude.", "options": {"A": "2√3"}, "worked_solution": ""}),
    ("standard_trig_only", {"question_text": "A ramp at 30°. Find sin(30°).", "options": {"A": "0.5"}, "worked_solution": "sin(30°) = 1/2"}),
    ("g_equals_ten", {"question_text": "A 2 kg mass falls. Find the force.", "options": {"A": "20 N"}, "worked_solution": "F = mg = 2 × 10 = 20 N"}),
    ("two_dp_decimal_ok", {"question_text": "What is 0.25 + 0.5?", "options": {"A": "0.75"}, "worked_solution": "Add: 0.25 + 0.50 = 0.75"}),
    ("log_power_of_two_ok", {"question_text": "Compute log_2(8).", "options": {"A": "3"}, "worked_solution": "2^3 = 8"}),
]


def test_pass_cases():
    for name, q in PASS_CASES:
        result = cc.check(q)
        assert result["pass"], f"{name} should pass: {result['issues']}"


# ---------------------------------------------------------------------------
# Fail cases (one per rule branch — exceeds the 10+ requirement)
# ---------------------------------------------------------------------------

FAIL_CASES = [
    ("non_perfect_square_root", {"question_text": "Find √17.", "options": {"A": "4.123"}, "worked_solution": "√17 ≈ 4.123"}),
    ("non_standard_trig_angle", {"question_text": "Find sin(23°).", "options": {"A": "0.39"}, "worked_solution": "sin(23°)"}),
    ("ugly_decimal", {"question_text": "What is 7.382 m/s?", "options": {"A": "7.382"}, "worked_solution": ""}),
    ("ugly_multiplication", {"question_text": "Compute 37 × 43.", "options": {"A": "1591"}, "worked_solution": "37 × 43 = 1591"}),
    ("g_value_9_8", {"question_text": "Falling mass, use g = 9.81.", "options": {"A": "19.62 N"}, "worked_solution": "F = 2 × 9.81 = 19.62"}),
    ("log_calculator", {"question_text": "Compute log(7).", "options": {"A": "0.845"}, "worked_solution": "log(7)"}),
]


def test_fail_cases():
    for name, q in FAIL_CASES:
        result = cc.check(q)
        assert not result["pass"], f"{name} should fail"
        assert result["issues"], f"{name} should report at least one issue"


def test_at_least_ten_distinct_cases():
    """ESA-22 acceptance: 10+ test cases covering each rule."""
    total = len(PASS_CASES) + len(FAIL_CASES)
    assert total >= 10
