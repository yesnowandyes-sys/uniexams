"""Tests for the biology factual-judge gate."""

from __future__ import annotations

import bio_judge  # type: ignore


SAMPLE_BIO_Q = {
    "module": "biology",
    "topic": "cells",
    "question_text": "Which organelle is the site of photosynthesis in plant cells?",
    "options": {
        "A": "Mitochondrion", "B": "Chloroplast",
        "C": "Nucleus", "D": "Ribosome", "E": "Lysosome",
    },
    "correct_answer": "B",
    "worked_solution": "Chloroplasts contain chlorophyll and conduct photosynthesis.",
}


def test_consistent_passes(stub_haiku):
    stub_haiku.responses = [{"text": "VERDICT: CONSISTENT", "cost_usd": 0.0005}]
    result = bio_judge.check(SAMPLE_BIO_Q)
    assert result["pass"]
    assert result["score"] == 1.0


def test_inconsistent_fails_with_detail(stub_haiku):
    stub_haiku.responses = [{"text": "VERDICT: INCONSISTENT ribosomes not in plant cells", "cost_usd": 0.0005}]
    result = bio_judge.check(SAMPLE_BIO_Q)
    assert not result["pass"]
    assert result["score"] == 0.0
    assert "ribosomes" in result["reason"]


def test_unsolvable_passes_with_half_score(stub_haiku):
    stub_haiku.responses = [{"text": "VERDICT: UNSOLVABLE", "cost_usd": 0.0005}]
    result = bio_judge.check(SAMPLE_BIO_Q)
    assert result["pass"]
    assert result["score"] == 0.5


def test_prompt_cache_flag_set_on_system_prompt(stub_haiku):
    """ESA-22 acceptance: Haiku calls use prompt caching for the Bio Spec."""
    stub_haiku.responses = [{"text": "VERDICT: CONSISTENT", "cost_usd": 0.0}]
    bio_judge.check(SAMPLE_BIO_Q)
    assert stub_haiku["calls"], "should have called Haiku at least once"
    assert stub_haiku["calls"][0]["cache_system_prompt"] is True
    # The Bio Content Spec must be embedded in the cached system prompt.
    assert "SPEC" in stub_haiku["calls"][0]["system_prompt"]


def test_api_failure_fails_gracefully(stub_haiku, monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("network down")
    monkeypatch.setattr(bio_judge, "call_haiku", _boom)
    result = bio_judge.check(SAMPLE_BIO_Q)
    assert not result["pass"]
    assert "API call failed" in result["reason"]
