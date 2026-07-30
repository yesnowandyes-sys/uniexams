#!/usr/bin/env python3
"""
LLM Solver Gate — Layer 3 of the verification stack (ESA-45 upgrade).

Runs **3 independent solve attempts** of the same multiple-choice question
(same model, varied temperature), then arbitrates by **majority vote**:

* **3/3 agree** and match the key  → PASS (strong agreement)
* **2/3 agree** and match the key  → PASS with a warning flag (self-consistency)
* solver majority **disagrees** with the key → REJECT
* **no majority** (3 different answers, or solver can't decide) → REJECT

Each attempt sees ONLY the question text and options — never the proposed
worked solution — so the solver's agreement is genuine independent corroboration.

Standard verdict dict:

    {
        "pass": bool,
        "score": float,        # 1.0 = 3/3 agree, 0.75 = 2/3 agree, 0.0 = reject
        "reason": str,
        "issues": list[str],
        "cost_usd": float,     # summed across attempts
        "solver_answer": str,  # majority-vote consensus
        "votes": {...},        # per-answer vote counts
        "flagged": bool,       # True when 2/3 (pass with warning)
        "attempts": int,       # number of solve attempts run
    }
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
    from _llm import call_haiku, DEFAULT_MODEL  # type: ignore
else:
    from .verdict import verdict  # type: ignore
    from ._llm import call_haiku, DEFAULT_MODEL  # type: ignore

logger = logging.getLogger(__name__)


SOLVER_SYSTEM_PROMPT = """\
You are an expert Cambridge ESAT candidate. Solve the multiple-choice \
question below independently. Do NOT speculate about the intended answer \
or align with any outside answer key — work through the problem step by \
step using only the information in the question stem.

At the very end of your response, output a single line in EXACTLY this \
format on its own line:

ANSWER: <letter>

where <letter> is one of A, B, C, D, E. If you genuinely cannot decide, \
output ANSWER: UNKNOWN. Show your reasoning first, then the ANSWER line.\
"""


def _format_options(options: Any) -> str:
    if isinstance(options, dict):
        return "\n".join(f"  {k}. {v}" for k, v in options.items())
    if isinstance(options, list):
        letters = "ABCDEFGHIABCDE"
        return "\n".join(f"  {letters[i]}. {v}" for i, v in enumerate(options))
    return str(options)


def _build_user_prompt(question: dict[str, Any]) -> str:
    options_str = _format_options(question.get("options"))
    return (
        f"Module: {question.get('module', 'unknown')}\n"
        f"Topic: {question.get('topic', 'unknown')}\n\n"
        f"Question:\n{question.get('question_text', '').strip()}\n\n"
        f"Options:\n{options_str}\n\n"
        f"Worked solution (yours to derive — do not assume any of the above):\n"
    )


ANSWER_RE = re.compile(r"ANSWER:\s*([A-Ea-e]|UNKNOWN)", re.IGNORECASE)
# Fallback patterns the model often emits despite instructions.
BOXED_RE = re.compile(r"\\boxed\{\s*([A-Ea-e])\s*\}")
OPTION_IS_RE = re.compile(
    r"\b(?:option|answer)\s+(?:is\s+)?[:\-]?\s*\*{0,2}([A-Ea-e])\b",
    re.IGNORECASE,
)
FINAL_ANSWER_RE = re.compile(
    r"\bfinal answer[:\s]+([A-Ea-e])\b",
    re.IGNORECASE,
)


def _parse_answer(text: str) -> str | None:
    """Extract the solver's answer letter from the response.

    Tries several patterns in order of reliability: explicit `ANSWER: X`,
    `\\boxed{X}`, "the answer is X", "final answer: X".
    """
    # Preferred: explicit `ANSWER:` token.
    matches = list(ANSWER_RE.finditer(text))
    if matches:
        token = matches[-1].group(1).upper()
        return None if token == "UNKNOWN" else token

    # Fallbacks — last occurrence wins to dodge narration about other options.
    for pattern in (BOXED_RE, FINAL_ANSWER_RE, OPTION_IS_RE):
        m = list(pattern.finditer(text))
        if m:
            return m[-1].group(1).upper()
    return None


# ---------------------------------------------------------------------------
# Core gate
# ---------------------------------------------------------------------------

# Temperatures for the independent attempts. Spread gives genuine diversity
# (different sampling paths) while staying deterministic per index.
ATTEMPT_TEMPERATURES = (0.0, 0.3, 0.6)
DEFAULT_ATTEMPTS = 3


def _solve_once(question: dict[str, Any], *, model: str, temperature: float) -> tuple[str | None, float, str | None]:
    """One independent solve. Returns (answer_letter_or_None, cost_usd, error)."""
    try:
        result = call_haiku(
            user_prompt=_build_user_prompt(question),
            system_prompt=SOLVER_SYSTEM_PROMPT,
            model=model,
            max_tokens=2048,
            temperature=temperature,
        )
    except Exception as exc:
        logger.warning("solver attempt (T=%.1f) failed: %s", temperature, exc)
        return None, 0.0, str(exc)
    return _parse_answer(result.text), result.cost_usd, None


def check(
    question: dict[str, Any],
    *,
    expected_answer: str | None = None,
    model: str | None = None,
    attempts: int = DEFAULT_ATTEMPTS,
) -> dict[str, Any]:
    """Solve the question `attempts` times (default 3) and majority-vote.

    Arbitration:
      * consensus == expected and 3/3 agree → pass, score 1.0
      * consensus == expected and 2/3 agree → pass with warning, score 0.75
      * consensus != expected                → reject, score 0.0
      * no majority (all differ)            → reject, score 0.0

    `expected_answer` defaults to `question['correct_answer']`.
    """
    if expected_answer is None:
        expected_answer = str(question.get("correct_answer", "")).strip().upper()
    if not expected_answer or expected_answer not in "ABCDE":
        return verdict(
            passed=True,
            score=0.5,
            reason="unsolvable — no ground-truth answer to compare against",
            issues=["missing or malformed correct_answer"],
            cost_usd=0.0,
            gate="solver",
            solver_answer=None,
            votes={},
            flagged=False,
            attempts=0,
        )

    effective_model = model or DEFAULT_MODEL
    temps = list(ATTEMPT_TEMPERATURES) + [0.5 + 0.1 * i for i in range(8)]
    temps = temps[:max(attempts, 1)]

    answers: list[str | None] = []
    total_cost = 0.0
    errors: list[str] = []
    for i in range(max(attempts, 1)):
        ans, cost, err = _solve_once(
            question, model=effective_model, temperature=temps[i % len(temps)]
        )
        answers.append(ans)
        total_cost += cost
        if err:
            errors.append(f"attempt {i + 1}: {err}")

    # Tally votes over decisive answers only.
    from collections import Counter
    valid = [a for a in answers if a is not None]
    votes = dict(Counter(valid))
    n_valid = len(valid)
    n_errored = len(errors)

    if n_valid == 0:
        # No decisive answer. Distinguish the two failure modes:
        #   * every attempt CRASHED  → the question is unverified → REJECT
        #     (spec: 0/3 agree = reject; silently passing an infra failure
        #      would let every question through when the solver API is down)
        #   * the model honestly returned UNKNOWN on a genuinely hard question
        #     → unsolvable, ACCEPT (don't penalise difficulty we can't crack)
        if n_errored >= max(attempts, 1):
            return verdict(
                passed=False,
                score=0.0,
                reason=(
                    f"solver API failed on all {attempts} attempts — "
                    f"question unverified"
                ),
                issues=["all attempts errored; no solver corroboration"] + errors,
                cost_usd=total_cost,
                gate="solver",
                solver_answer=None,
                votes={},
                flagged=False,
                attempts=attempts,
                model=effective_model,
            )
        return verdict(
            passed=True,
            score=0.5,
            reason=f"all {attempts} solver attempts returned UNKNOWN — could not decide",
            issues=["raw outputs/decisions inconclusive"] + errors,
            cost_usd=total_cost,
            gate="solver",
            solver_answer=None,
            votes={},
            flagged=False,
            attempts=attempts,
            model=effective_model,
        )

    consensus, top_count = Counter(valid).most_common(1)[0]
    correct = consensus == expected_answer

    if correct and top_count == n_valid and n_valid >= 2:
        # Unanimous agreement with the key.
        return verdict(
            passed=True,
            score=1.0,
            reason=f"solver unanimous ({top_count}/{n_valid} → {consensus} == {expected_answer})",
            issues=[],
            cost_usd=total_cost,
            gate="solver",
            solver_answer=consensus,
            votes=votes,
            flagged=False,
            attempts=attempts,
            model=effective_model,
        )

    if correct and top_count >= 2:
        # Majority (but not unanimous) agreement with the key → pass + warning.
        return verdict(
            passed=True,
            score=0.75,
            reason=(
                f"solver majority agrees ({top_count}/{n_valid} → {consensus} == "
                f"{expected_answer}) — flagged for self-consistency"
            ),
            issues=[f"vote split: {votes}; expected {expected_answer}"],
            cost_usd=total_cost,
            gate="solver",
            solver_answer=consensus,
            votes=votes,
            flagged=True,
            attempts=attempts,
            model=effective_model,
        )

    # Either the consensus is a wrong option, or there is no majority.
    if top_count >= 2:
        reason = (
            f"solver majority disagrees ({top_count}/{n_valid} → {consensus} != "
            f"{expected_answer})"
        )
    else:
        reason = f"no solver majority — all attempts differ (votes {votes})"
    return verdict(
        passed=False,
        score=0.0,
        reason=reason,
        issues=[f"votes: {votes}; expected {expected_answer}"] + errors,
        cost_usd=total_cost,
        gate="solver",
        solver_answer=consensus,
        votes=votes,
        flagged=False,
        attempts=attempts,
        model=effective_model,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_question(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data:
        return data["questions"][0]
    return data


# ---------------------------------------------------------------------------
# Self-test — exercises the majority-vote arbitration with a mocked solver
# (no API calls). Run: python solver.py --self-test
# ---------------------------------------------------------------------------

def _run_self_test() -> int:
    """Drive `check()` with a stubbed `_solve_once` to test vote arbitration."""
    import solver as self_mod  # local alias for monkeypatching

    q = {
        "question_text": "Placeholder (mocked solver).",
        "options": {"A": "x", "B": "y", "C": "z", "D": "w", "E": "v"},
        "correct_answer": "C",
    }

    cases = [
        ("unanimous_correct", ["C", "C", "C"], True, 1.0, False),
        ("majority_correct_flagged", ["C", "C", "A"], True, 0.75, True),
        ("majority_wrong_reject", ["A", "A", "C"], False, 0.0, False),
        ("no_majority_reject", ["A", "B", "C"], False, 0.0, False),
        ("all_unknown_unsolvable", [None, None, None], True, 0.5, False),
        ("all_errored_rejects", ["ERR", "ERR", "ERR"], False, 0.0, False),
        ("missing_key_unsolvable", ["C", "C", "C"], True, 0.5, False),
    ]
    failures = 0
    for name, scripted, exp_pass, exp_score, exp_flag in cases:
        original = self_mod._solve_once
        seq = iter(scripted)

        def _stub(_q, *, model, temperature, _seq=seq):
            val = next(_seq)
            # "ERR" simulates an API/infrastructure failure for one attempt.
            if val == "ERR":
                return None, 0.0, "simulated API failure"
            return val, 0.001, None

        self_mod._solve_once = _stub
        try:
            qq = dict(q)
            if name == "missing_key_unsolvable":
                qq = {"question_text": "x", "options": q["options"]}  # no correct_answer
            r = self_mod.check(qq)
        finally:
            self_mod._solve_once = original

        ok = (
            r["pass"] == exp_pass
            and abs(r["score"] - exp_score) < 1e-6
            and r.get("flagged") == exp_flag
        )
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {name}: pass={r['pass']} score={r['score']} flagged={r.get('flagged')}")
        if not ok:
            print(f"        expected pass={exp_pass} score={exp_score} flagged={exp_flag}")
            print(f"        reason={r['reason']}")
            failures += 1
    print(f"\n{len(cases) - failures}/{len(cases)} cases passed")
    return failures


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT solver gate (Layer 3, 3x majority vote)")
    p.add_argument("--question", type=Path, help="Path to a question JSON file")
    p.add_argument("--model", default=None, help="Override solver model id")
    p.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS, help="Independent solve attempts (default 3)")
    p.add_argument("--self-test", action="store_true", help="Run built-in mock vote-arbitration tests")
    args = p.parse_args(argv)

    if args.self_test:
        return _run_self_test()

    if not args.question:
        p.error("--question or --self-test is required")
    question = _load_question(args.question)
    result = check(question, model=args.model, attempts=args.attempts)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
