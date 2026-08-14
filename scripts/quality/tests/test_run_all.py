"""Tests for the end-to-end `run_all` orchestrator."""

from __future__ import annotations

import run_all  # type: ignore


def test_run_all_gates_match_current_spec():
    """ESA-45 replaced GATES with a fixed 6-gate stack (no more subject-based
    skipping of chem_stoich/bio_judge -- those gates no longer exist). `skip`
    is a generic opt-out any caller can use for any gate key."""
    q = {"module": "maths1", "question_text": "What is 1+1?",
         "options": {"A": "2"}, "correct_answer": "A",
         "worked_solution": "1 + 1 = 2"}
    summary = run_all.run_all(q, skip={"solver", "factual_check"})
    assert set(summary["gates"]) == {key for key, _, _ in run_all.GATES}
    assert summary["gates"]["solver"]["skipped"]
    assert summary["gates"]["factual_check"]["skipped"]
    assert not summary["gates"]["calculability"]["skipped"]


def test_run_all_runs_chem_for_chemistry():
    """A chemistry question runs through the current gate stack (sympy_verify,
    structural_difficulty, etc.) without crashing -- there's no chemistry-only
    gate to assert on anymore post-ESA-45."""
    q = {"module": "chemistry", "question_text": "Balance: CH4 + O2 -> CO2 + H2O",
         "options": {"A": "CH4 + 2O2 -> CO2 + 2H2O"}, "correct_answer": "A",
         "worked_solution": "CH4 + 2O2 -> CO2 + 2H2O"}
    summary = run_all.run_all(q, skip={"solver", "factual_check"}, short_circuit=False)
    for key, result in summary["gates"].items():
        if not result["skipped"]:
            assert "gate crashed" not in str(result.get("reason", "")), (key, result)


def test_run_all_reports_within_budget(stub_haiku, sample_maths_question):
    """ESA-22 acceptance: total per-question API cost ≤ $0.005."""
    # Solver + reviewer with cheap stubs.
    stub_haiku.responses = [
        {"text": "ANSWER: D", "cost_usd": 0.0015},       # solver
        {"text": "CLARITY: 5\nSYLLABUS: 5\nDISTRACTORS: 4\nUNIQUENESS: 4",
         "cost_usd": 0.00125},                            # reviewer
    ]
    summary = run_all.run_all(sample_maths_question, skip={"bio_judge"})
    total = summary["total_cost_usd"]
    assert total <= run_all.COST_BUDGET_USD, (
        f"cost ${total:.6f} exceeds budget ${run_all.COST_BUDGET_USD:.6f}"
    )
    assert summary["within_budget"]


def test_run_all_overall_pass_logic(sample_maths_question):
    """If every active gate passes, summary.pass should be True."""
    summary = run_all.run_all(sample_maths_question, skip={"solver", "reviewer", "bio_judge"})
    assert summary["pass"]
