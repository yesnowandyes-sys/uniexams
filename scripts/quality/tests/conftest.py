"""Shared pytest fixtures for the quality-gate tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the quality package importable both as a package and flat.
QUALITY_DIR = Path(__file__).resolve().parent.parent
if str(QUALITY_DIR) not in sys.path:
    sys.path.insert(0, str(QUALITY_DIR))


class StubLLMResult:
    """Mimics `_llm.LLMResult` so the gates don't need the network."""

    def __init__(self, text: str, cost_usd: float = 0.0):
        self.text = text
        self.cost_usd = cost_usd
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_tokens = 0
        self.cache_creation_tokens = 0
        self.model = "stub"


class StubState:
    """Dict-like stub state that also supports attribute access.

    Tests may use either `stub.responses = [...]` or `stub["responses"] = [...]`,
    and either `stub["calls"]` or `stub.calls`.
    """

    __slots__ = ("responses", "calls")

    def __init__(self):
        self.responses = []
        self.calls = []

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __contains__(self, key):
        return hasattr(self, key)


@pytest.fixture
def stub_haiku(monkeypatch):
    """Replace `_llm.call_haiku` with a stub that yields canned responses.

    Tests register expected responses via `stub_haiku.responses = [...]`
    or `stub_haiku["responses"] = [...]` (both supported).
    """
    state = StubState()

    def _fake_call_haiku(*, user_prompt, system_prompt="", model=None,
                          max_tokens=2048, cache_system_prompt=False,
                          temperature=0.0):
        state.calls.append({
            "user_prompt": user_prompt,
            "system_prompt": system_prompt,
            "cache_system_prompt": cache_system_prompt,
        })
        if not state.responses:
            return StubLLMResult(text="ANSWER: UNKNOWN", cost_usd=0.0)
        return StubLLMResult(**state.responses.pop(0))

    # Patch in every module that imported `call_haiku`.
    import solver  # type: ignore
    import reviewer  # type: ignore
    import bio_judge  # type: ignore
    monkeypatch.setattr(solver, "call_haiku", _fake_call_haiku)
    monkeypatch.setattr(reviewer, "call_haiku", _fake_call_haiku)
    monkeypatch.setattr(bio_judge, "call_haiku", _fake_call_haiku)
    return state


@pytest.fixture
def sample_maths_question():
    return {
        "module": "maths1",
        "topic": "algebra",
        "question_text": (
            "A function f is defined by f(x) = 2x + 3. "
            "What is f(4)?"
        ),
        "options": {"A": "5", "B": "7", "C": "9", "D": "11", "E": "12"},
        "correct_answer": "D",
        "worked_solution": "f(4) = 2(4) + 3 = 11, so the answer is D.",
    }
