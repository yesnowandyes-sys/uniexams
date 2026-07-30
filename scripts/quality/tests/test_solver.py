"""Tests for the LLM solver gate (Layer 3) — 3× majority-vote arbitration.

The ESA-45 upgrade replaced the single-shot solver with three independent solve
attempts arbitrated by majority vote:

    3/3 agree w/ key -> PASS (score 1.0)
    2/3 agree w/ key -> PASS + warning flag (score 0.75)
    majority wrong   -> REJECT (score 0.0)
    no majority      -> REJECT (score 0.0)
    all UNKNOWN      -> unsolvable, ACCEPT (score 0.5)
    all API errors   -> REJECT — question unverified (score 0.0)
"""

from __future__ import annotations

import solver  # type: ignore


def test_solver_unanimous_correct(stub_haiku, sample_maths_question):
    """3/3 attempts agree with the key → pass, score 1.0, not flagged."""
    stub_haiku.responses = [{"text": "ANSWER: D", "cost_usd": 0.001}] * 3
    result = solver.check(sample_maths_question)
    assert result["pass"]
    assert result["score"] == 1.0
    assert result["solver_answer"] == "D"
    assert result["flagged"] is False
    assert result["attempts"] == 3
    assert result["cost_usd"] == 0.003  # summed across the 3 attempts


def test_solver_majority_correct_flagged(stub_haiku, sample_maths_question):
    """2/3 agree with the key → pass with a self-consistency warning."""
    stub_haiku.responses = [
        {"text": "ANSWER: D", "cost_usd": 0.001},
        {"text": "ANSWER: D", "cost_usd": 0.001},
        {"text": "ANSWER: B", "cost_usd": 0.001},
    ]
    result = solver.check(sample_maths_question)
    assert result["pass"]
    assert result["score"] == 0.75
    assert result["solver_answer"] == "D"
    assert result["flagged"] is True


def test_solver_majority_wrong_rejects(stub_haiku, sample_maths_question):
    """Solver majority settles on a different option → reject."""
    stub_haiku.responses = [{"text": "ANSWER: B", "cost_usd": 0.001}] * 3
    result = solver.check(sample_maths_question)
    assert not result["pass"]
    assert result["score"] == 0.0
    assert result["solver_answer"] == "B"
    assert "B != D" in result["reason"]


def test_solver_no_majority_rejects(stub_haiku, sample_maths_question):
    """Three different answers, no majority → reject."""
    stub_haiku.responses = [
        {"text": "ANSWER: A", "cost_usd": 0.001},
        {"text": "ANSWER: B", "cost_usd": 0.001},
        {"text": "ANSWER: C", "cost_usd": 0.001},
    ]
    result = solver.check(sample_maths_question)
    assert not result["pass"]
    assert result["score"] == 0.0


def test_solver_picks_boxed_letter(stub_haiku, sample_maths_question):
    """Model emits \\boxed{D} instead of ANSWER: D — must still resolve."""
    stub_haiku.responses = [{"text": "...so \\boxed{D}", "cost_usd": 0.0}] * 3
    result = solver.check(sample_maths_question)
    assert result["pass"]
    assert result["solver_answer"] == "D"


def test_solver_all_unknown_unsolvable(stub_haiku, sample_maths_question):
    """All 3 attempts return UNKNOWN → unsolvable (accept, score 0.5)."""
    stub_haiku.responses = [{"text": "ANSWER: UNKNOWN", "cost_usd": 0.001}] * 3
    result = solver.check(sample_maths_question)
    assert result["pass"]
    assert result["score"] == 0.5
    assert "UNKNOWN" in result["reason"].upper()


def test_solver_missing_ground_truth(stub_haiku):
    """No correct_answer to compare against → unsolvable, no API call made."""
    q = {"module": "maths1", "question_text": "What?", "options": {"A": "1"}}
    result = solver.check(q)
    assert result["pass"]
    assert result["score"] == 0.5
    assert stub_haiku["calls"] == []  # returns before any solve attempt


def test_solver_api_failure_all_crash_rejects(
    stub_haiku, sample_maths_question, monkeypatch
):
    """Every attempt's API call crashes → reject (question unverified).

    This is distinct from the model honestly returning UNKNOWN: an
    infrastructure failure must NOT silently pass, otherwise the solver gate
    rubber-stamps every question when its API is down.
    """
    def _boom(**kwargs):
        raise RuntimeError("network down")
    monkeypatch.setattr(solver, "call_haiku", _boom)
    result = solver.check(sample_maths_question)
    assert not result["pass"]
    assert result["score"] == 0.0
    assert "API failed" in result["reason"]
