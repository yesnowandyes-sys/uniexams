"""Tests for the LLM reviewer rubric gate (Gate 4)."""

from __future__ import annotations

import reviewer  # type: ignore


def _scores_response(c, s, d, u, diff=3, cost=0.00125):
    text = (
        f"CLARITY: {c}\nSYLLABUS: {s}\nDISTRACTORS: {d}\n"
        f"UNIQUENESS: {u}\nDIFFICULTY: {diff}"
    )
    return {"text": text, "cost_usd": cost}


def test_reviewer_all_above_threshold(stub_haiku, sample_maths_question):
    stub_haiku.responses = [_scores_response(5, 5, 4, 4)]
    result = reviewer.check(sample_maths_question)
    assert result["pass"]
    assert result["scores"]["clarity"] == 5
    assert result["cost_usd"] == 0.00125


def test_reviewer_one_dim_below_threshold(stub_haiku, sample_maths_question):
    """Blocking dim below threshold fails the question."""
    stub_haiku.responses = [_scores_response(5, 5, 2, 4)]
    result = reviewer.check(sample_maths_question)
    assert not result["pass"]
    assert "distractors" in result["reason"]
    assert "distractors=2" in result["issues"][0]


def test_reviewer_difficulty_is_advisory_and_scored(stub_haiku, sample_maths_question):
    """ESA-62: DIFFICULTY is parsed and recorded but never gates the question."""
    stub_haiku.responses = [_scores_response(5, 5, 4, 4, diff=5)]
    result = reviewer.check(sample_maths_question)
    assert result["pass"]
    assert result["scores"]["difficulty"] == 5
    assert result["difficulty_score_llm"] == 5
    assert result["difficulty_band_llm"] == "very_hard"


def test_reviewer_low_difficulty_does_not_block(stub_haiku, sample_maths_question):
    stub_haiku.responses = [_scores_response(5, 5, 4, 4, diff=1)]
    result = reviewer.check(sample_maths_question)
    assert result["pass"], "difficulty alone must not block"
    assert result["scores"]["difficulty"] == 1
    assert result["difficulty_band_llm"] == "easy"


def test_reviewer_unparseable(stub_haiku, sample_maths_question):
    stub_haiku.responses = [{"text": "I don't understand", "cost_usd": 0.0}]
    result = reviewer.check(sample_maths_question)
    assert not result["pass"]
    assert result["scores"] == {}


def test_reviewer_threshold_override(stub_haiku, sample_maths_question):
    """ESA-22 acceptance: each blocking dim ≥ 4 by default, configurable."""
    stub_haiku.responses = [_scores_response(4, 4, 4, 4)]
    result = reviewer.check(sample_maths_question, threshold=5)
    assert not result["pass"]  # all 4s are below threshold=5


def test_reviewer_uniqueness_is_advisory_not_blocking(stub_haiku, sample_maths_question):
    """ESA-37: a standard textbook-style question (uniqueness=3) still passes.

    Template-derived questions routinely score 3 on the uniqueness rubric.
    `scripts/dedup.py` is the authoritative duplicate guard; the reviewer's
    uniqueness score is recorded but does not gate acceptance.
    """
    stub_haiku.responses = [_scores_response(5, 5, 5, 3)]
    result = reviewer.check(sample_maths_question)
    assert result["pass"], f"expected pass, got reason: {result['reason']!r}"
    assert result["scores"]["uniqueness"] == 3
    assert result["advisory"] == [], "uniqueness=3 should not trip advisory"


def test_reviewer_low_uniqueness_surfaces_advisory(stub_haiku, sample_maths_question):
    """uniqueness below the advisory floor still passes but is flagged."""
    stub_haiku.responses = [_scores_response(5, 5, 5, 1)]
    result = reviewer.check(sample_maths_question)
    assert result["pass"], "uniqueness alone must not block"
    assert result["scores"]["uniqueness"] == 1
    assert any("uniqueness" in a for a in result["advisory"]), (
        f"expected uniqueness advisory, got: {result['advisory']!r}"
    )


def test_reviewer_blocking_dims_override(stub_haiku, sample_maths_question):
    """Operator can re-enable uniqueness as a blocking dim if they want."""
    stub_haiku.responses = [_scores_response(5, 5, 5, 3)]
    result = reviewer.check(
        sample_maths_question,
        blocking_dims=("clarity", "syllabus", "distractors", "uniqueness"),
    )
    assert not result["pass"]
    assert "uniqueness" in result["reason"]
