"""Tests for the end-to-end `run_all` orchestrator."""

from __future__ import annotations

import run_all  # type: ignore


def test_run_all_skips_irrelevant_subject_gates():
    """A maths1 question should auto-skip chem_stoich and bio_judge."""
    q = {"module": "maths1", "question_text": "What is 1+1?",
         "options": {"A": "2"}, "correct_answer": "A",
         "worked_solution": "1 + 1 = 2"}
    summary = run_all.run_all(q, skip={"solver", "reviewer"})
    assert summary["gates"]["chem_stoich"]["skipped"]
    assert summary["gates"]["bio_judge"]["skipped"]
    assert not summary["gates"]["calculator"]["skipped"]


def test_run_all_runs_chem_for_chemistry():
    q = {"module": "chemistry", "question_text": "Balance: ?",
         "options": {"A": "?"}, "correct_answer": "A",
         "worked_solution": "CH4 + 2O2 → CO2 + 2H2O"}
    summary = run_all.run_all(q, skip={"solver", "reviewer"})
    assert not summary["gates"]["chem_stoich"]["skipped"]
    assert summary["gates"]["chem_stoich"]["pass"]


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
