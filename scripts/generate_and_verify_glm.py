#!/usr/bin/env python3
"""
ESA-41: GLM-5.2 generate-then-verify script with quota gating.

Strict loop: generate one question via GLM-5.2 → immediately verify it
(using GLM-5.2 for LLM-based gates) → if it passes, insert into DB →
generate the next → verify → etc. Failed questions are logged and
discarded (not inserted).

Usage:
    python3 generate_and_verify_glm.py                # run until quota exhausted
    python3 generate_and_verify_glm.py --max N        # stop after N verified questions
    python3 generate_and_verify_glm.py --dry-run      # show plan, don't call API
    python3 generate_and_verify_glm.py --spec-code PHYS.P1 --difficulty Easy

Environment:
    ZAI_API_KEY  — Required. z.ai API key.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import math
import os
import random
import re
import signal
import sqlite3
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import openai

# Make sibling modules importable
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import generator_glm

logger = logging.getLogger("generate_and_verify_glm")

# ──────────────────────────────────────────────────────────────────────────
# Constants (reused from generator_glm.py)
# ──────────────────────────────────────────────────────────────────────────

SHARED_DIR = SCRIPTS_DIR.parent
PATTERNS_DIR = SHARED_DIR / "patterns"
DB_PATH = SHARED_DIR / "data" / "questions.db"

VALID_DIFFICULTIES = generator_glm.VALID_DIFFICULTIES
ZAI_BASE_URL = generator_glm.ZAI_BASE_URL
DEFAULT_MODEL = generator_glm.DEFAULT_MODEL
MAX_TOKENS = 32768

# Quota guard — block generation when usage exceeds expected usage.
# Expected usage = elapsedPct * this multiplier.
# Only run when actual percentage <= QUOTA_USAGE_MULTIPLIER * elapsedPct.
QUOTA_USAGE_MULTIPLIER = 0.9

# Floor thresholds — below these elapsed percentages, allow generation unconditionally
FIVE_HOUR_FLOOR_PCT = 10
WEEKLY_FLOOR_PCT = 1

# Lock file to prevent concurrent runs (e.g. overlapping cron triggers)
LOCK_FILE = SCRIPTS_DIR / ".generate_and_verify_glm.lock"

# Quota check: use the local dashboard endpoint (same as generator_glm.py).
# The dashboard pre-computes elapsedPct correctly; calling z.ai directly
# and computing it ourselves was producing wrong values.
_LOCAL_QUOTA_URL = "http://127.0.0.1:8081/api/zai-quota"

# Graceful shutdown
_shutdown = False

# Max runtime support
_start_time: float = 0.0
_max_runtime_s: float = 0.0  # 0 = no limit

# Retry-with-feedback settings
MAX_REVISION_RETRIES = 3  # up to 3 retries (4 total attempts including original)


def _handle_sigint(signum: int, frame: Any) -> None:
    global _shutdown
    if _shutdown:
        logger.info("Second SIGINT — forcing exit.")
        sys.exit(130)
    _shutdown = True
    logger.info("SIGINT received — finishing current question, then exiting...")


signal.signal(signal.SIGINT, _handle_sigint)

# ──────────────────────────────────────────────────────────────────────────
# Quality gates — deterministic (import directly)
# ──────────────────────────────────────────────────────────────────────────

QUALITY_DIR = SCRIPTS_DIR / "quality"
sys.path.insert(0, str(QUALITY_DIR))
import calculator_check  # noqa: E402
import sympy_verifier  # noqa: E402
import chem_stoich_check  # noqa: E402
import verdict as verdict_mod  # noqa: E402

# ──────────────────────────────────────────────────────────────────────────
# GLM-5.2 LLM adapter for LLM-based gates (solver, reviewer, bio_judge)
# ──────────────────────────────────────────────────────────────────────────

# We replicate the prompts from solver.py, reviewer.py, bio_judge.py here
# and route through the OpenAI client pointed at GLM-5.2.

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

REVIEWER_SYSTEM_PROMPT = """\
You are a senior ESAT examiner reviewing a draft question for the ESAT \
practice question bank. Score each of the four rubric dimensions 1–5, \
where 1 is unacceptable and 5 is exemplary.

Use the following rubric:

CLARITY:
  5 — Wording is unambiguous; all necessary information is present.
  4 — Minor wording could be tightened but solvable as written.
  3 — Some ambiguity; a careful student might still solve it.
  2 — Material ambiguity that affects solvability.
  1 — Unsolvable or self-contradictory as written.

SYLLABUS (match to ESAT Content Specification):
  5 — Plainly within syllabus for the stated module.
  4 — Within syllabus, borderline topic but reasonable.
  3 — Borderline; could be argued either way.
  2 — Likely out of syllabus or off-spec (e.g. g=9.81).
  1 — Clearly out of syllabus.

DISTRACTORS (plausibility of wrong options):
  5 — Every distractor corresponds to an identifiable student error.
  4 — All distractors plausible; one could be tighter.
  3 — One weak or absurd distractor.
  2 — Multiple weak distractors; right answer is obvious by elimination.
  1 — Distractors are obviously wrong / absurd values.

UNIQUENESS (advisory signal only — does NOT gate the question):
  5 — Novel context or twist; tests reasoning, not recall.
  4 — Standard topic but presented cleanly with a small twist.
  3 — Standard textbook-style question (expected median for practice bank).
  2 — Heavily templated; near-duplicate of common practice material.
  1 — Identical a well-known past paper question.
  Note: an embedding/shingle dedup pass against the existing corpus runs
  separately (scripts/dedup.py) and is the authoritative duplicate guard.

Output your review as FOUR lines in EXACTLY this format, in this order:

CLARITY: <int 1-5>
SYLLABUS: <int 1-5>
DISTRACTORS: <int 1-5>
UNIQUENESS: <int 1-5>

Do not output anything else. No prose. No commentary. Just the four lines.
"""

BIO_JUDGE_SYSTEM_PROMPT_TEMPLATE = """\
You are a Biology examiner reviewing a draft ESAT Biology question for \
factual correctness. Judge whether every factual claim in the question \
stem, options, and worked solution is consistent with A-level Biology \
content expected in the ESAT exam.

Judge whether every factual claim is consistent. Output one of:

VERDICT: CONSISTENT
or
VERDICT: INCONSISTENT
<one-line description of the contradiction>

or, if you genuinely cannot tell:

VERDICT: UNSOLVABLE

Do not output anything else.
"""


def _glm_call(
    client: openai.OpenAI,
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 2048,
) -> tuple[str, int, int]:
    """Call GLM-5.2 via OpenAI client. Returns (text, input_tokens, output_tokens)."""
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )
    text = response.choices[0].message.content or ""
    # Reasoning models put output in reasoning_content when content is empty
    reasoning = getattr(response.choices[0].message, 'reasoning_content', None) or ""
    if len(text.strip()) < 10 and reasoning.strip():
        text = reasoning
    usage = response.usage
    in_tok = usage.prompt_tokens if usage else 0
    out_tok = usage.completion_tokens if usage else 0
    return text, in_tok, out_tok


def _format_options(options: Any) -> str:
    if isinstance(options, dict):
        return "\n".join(f"  {k}. {v}" for k, v in options.items())
    if isinstance(options, list):
        letters = "ABCDE"
        return "\n".join(f"  {letters[i]}. {v}" for i, v in enumerate(options))
    return str(options)


# ──────────────────────────────────────────────────────────────────────────
# GLM-5.2 solver gate
# ──────────────────────────────────────────────────────────────────────────

SOLVER_ANSWER_RE = re.compile(r"ANSWER:\s*([A-Ea-e]|UNKNOWN)", re.IGNORECASE)
SOLVER_BOXED_RE = re.compile(r"\\boxed\{\s*([A-Ea-e])\s*\}")
SOLVER_OPTION_IS_RE = re.compile(
    r"\b(?:option|answer)\s+(?:is\s+)?[:\-]?\s*\*{0,2}([A-Ea-e])\b",
    re.IGNORECASE,
)
SOLVER_FINAL_ANSWER_RE = re.compile(
    r"\bfinal answer[:\s]+([A-Ea-e])\b",
    re.IGNORECASE,
)


def _parse_solver_answer(text: str) -> Optional[str]:
    matches = list(SOLVER_ANSWER_RE.finditer(text))
    if matches:
        token = matches[-1].group(1).upper()
        return None if token == "UNKNOWN" else token
    for pattern in (SOLVER_BOXED_RE, SOLVER_FINAL_ANSWER_RE, SOLVER_OPTION_IS_RE):
        m = list(pattern.finditer(text))
        if m:
            return m[-1].group(1).upper()
    return None


def _solver_check_glm(
    client: openai.OpenAI, question: dict[str, Any], model: str = DEFAULT_MODEL
) -> dict[str, Any]:
    """GLM-5.2 solver gate: independently solve and compare to correct_answer."""
    expected = str(question.get("correct_answer", "")).strip().upper()
    if not expected or expected not in "ABCDE":
        return verdict_mod.verdict(
            passed=True, score=0.5,
            reason="unsolvable — no ground-truth answer",
            issues=["missing or malformed correct_answer"], cost_usd=0.0, gate="solver",
        )

    options_str = _format_options(question.get("options"))
    user_prompt = (
        f"Module: {question.get('module', 'unknown')}\n"
        f"Topic: {question.get('spec_topic', 'unknown')}\n\n"
        f"Question:\n{question.get('question_text', '').strip()}\n\n"
        f"Options:\n{options_str}\n\n"
        f"Worked solution (yours to derive — do not assume any of the above):\n"
    )

    try:
        text, in_tok, out_tok = _glm_call(
            client, SOLVER_SYSTEM_PROMPT, user_prompt, model=model, max_tokens=8192,
        )
    except Exception as exc:
        return verdict_mod.verdict(
            passed=False, score=0.0,
            reason=f"solver GLM call failed: {exc}",
            issues=[str(exc)], cost_usd=0.0, gate="solver",
        )

    solver_answer = _parse_solver_answer(text)
    if solver_answer is None:
        return verdict_mod.verdict(
            passed=True, score=0.5,
            reason="solver returned UNKNOWN — could not decide",
            issues=[f"solver output: {text[:300]!r}"],
            cost_usd=0.0, gate="solver", solver_answer=None,
        )

    passed = solver_answer == expected
    return verdict_mod.verdict(
        passed=passed,
        score=1.0 if passed else 0.0,
        reason=(
            f"solver agrees ({solver_answer} == {expected})"
            if passed
            else f"solver disagrees ({solver_answer} != {expected})"
        ),
        issues=[] if passed else [f"solver picked {solver_answer}, expected {expected}"],
        cost_usd=0.0, gate="solver", solver_answer=solver_answer,
    )


# ──────────────────────────────────────────────────────────────────────────
# GLM-5.2 reviewer gate
# ──────────────────────────────────────────────────────────────────────────

DIMENSION_PATTERNS = {
    "clarity": re.compile(r"CLARITY:\s*(\d+)", re.IGNORECASE),
    "syllabus": re.compile(r"SYLLABUS:\s*(\d+)", re.IGNORECASE),
    "distractors": re.compile(r"DISTRACTORS:\s*(\d+)", re.IGNORECASE),
    "uniqueness": re.compile(r"UNIQUENESS:\s*(\d+)", re.IGNORECASE),
}
BLOCKING_DIMS = ("clarity", "syllabus", "distractors")
ACCEPT_THRESHOLD = 4


def _parse_reviewer_scores(text: str) -> Optional[dict[str, int]]:
    scores: dict[str, int] = {}
    for key, pattern in DIMENSION_PATTERNS.items():
        m = pattern.search(text)
        if not m:
            return None
        val = int(m.group(1))
        if not 1 <= val <= 5:
            return None
        scores[key] = val
    return scores


def _reviewer_check_glm(
    client: openai.OpenAI, question: dict[str, Any], model: str = DEFAULT_MODEL
) -> dict[str, Any]:
    """GLM-5.2 reviewer gate: score on clarity, syllabus, distractors, uniqueness."""
    options_str = _format_options(question.get("options"))
    correct = question.get("correct_answer", "unknown")
    solution = question.get("explanation") or ""
    user_prompt = (
        f"Module: {question.get('module', 'unknown')}\n"
        f"Topic: {question.get('spec_topic', 'unknown')}\n"
        f"Stated correct answer: {correct}\n\n"
        f"Question:\n{question.get('question_text', '').strip()}\n\n"
        f"Options:\n{options_str}\n\n"
        f"Worked solution:\n{solution.strip()}\n"
    )

    try:
        text, in_tok, out_tok = _glm_call(
            client, REVIEWER_SYSTEM_PROMPT, user_prompt, model=model, max_tokens=4096,
        )
    except Exception as exc:
        return verdict_mod.verdict(
            passed=False, score=0.0,
            reason=f"reviewer GLM call failed: {exc}",
            issues=[str(exc)], cost_usd=0.0, gate="reviewer", scores={},
        )

    scores = _parse_reviewer_scores(text)
    if scores is None:
        return verdict_mod.verdict(
            passed=False, score=0.0,
            reason="reviewer returned unparseable scores",
            issues=[f"raw: {text[:300]!r}"],
            cost_usd=0.0, gate="reviewer", scores={},
        )

    failed_dims = [k for k in BLOCKING_DIMS if scores.get(k, 0) < ACCEPT_THRESHOLD]
    mean_rubric = sum(scores[k] for k in BLOCKING_DIMS) / (5 * len(BLOCKING_DIMS))
    passed = not failed_dims

    return verdict_mod.verdict(
        passed=passed,
        score=round(mean_rubric, 3),
        reason=(
            f"all blocking dims >= {ACCEPT_THRESHOLD}"
            if passed
            else f"dims below {ACCEPT_THRESHOLD}: {', '.join(failed_dims)}"
        ),
        issues=[f"{k}={scores[k]} (<{ACCEPT_THRESHOLD})" for k in failed_dims],
        cost_usd=0.0, gate="reviewer", scores=scores,
    )


# ──────────────────────────────────────────────────────────────────────────
# GLM-5.2 biology judge gate
# ──────────────────────────────────────────────────────────────────────────

VERDICT_CONSISTENT = re.compile(r"VERDICT:\s*CONSISTENT", re.IGNORECASE)
VERDICT_INCONSISTENT = re.compile(r"VERDICT:\s*INCONSISTENT\s*(.*)", re.IGNORECASE)
VERDICT_UNSOLVABLE = re.compile(r"VERDICT:\s*UNSOLVABLE", re.IGNORECASE)


def _bio_judge_check_glm(
    client: openai.OpenAI, question: dict[str, Any], model: str = DEFAULT_MODEL
) -> dict[str, Any]:
    """GLM-5.2 biology factual judge gate."""
    options_str = _format_options(question.get("options"))
    solution = question.get("explanation") or ""
    user_prompt = (
        f"Stated correct answer: {question.get('correct_answer', 'unknown')}\n\n"
        f"Question:\n{question.get('question_text', '').strip()}\n\n"
        f"Options:\n{options_str}\n\n"
        f"Worked solution:\n{solution.strip()}\n"
    )

    try:
        text, in_tok, out_tok = _glm_call(
            client, BIO_JUDGE_SYSTEM_PROMPT_TEMPLATE, user_prompt,
            model=model, max_tokens=2048,
        )
    except Exception as exc:
        return verdict_mod.verdict(
            passed=False, score=0.0,
            reason=f"bio_judge GLM call failed: {exc}",
            issues=[str(exc)], cost_usd=0.0, gate="bio_judge",
        )

    text = text.strip()
    if VERDICT_UNSOLVABLE.search(text):
        return verdict_mod.verdict(
            passed=True, score=0.5,
            reason="judge returned UNSOLVABLE",
            issues=[], cost_usd=0.0, gate="bio_judge",
        )
    inconsistent = VERDICT_INCONSISTENT.search(text)
    if inconsistent:
        detail = inconsistent.group(1).strip()
        return verdict_mod.verdict(
            passed=False, score=0.0,
            reason=f"factual inconsistency: {detail or 'unspecified'}",
            issues=[detail or "judge flagged inconsistency"],
            cost_usd=0.0, gate="bio_judge",
        )
    if VERDICT_CONSISTENT.search(text):
        return verdict_mod.verdict(
            passed=True, score=1.0,
            reason="all claims consistent with spec",
            issues=[], cost_usd=0.0, gate="bio_judge",
        )
    return verdict_mod.verdict(
        passed=True, score=0.5,
        reason="judge returned unparseable verdict — treating as unsolvable",
        issues=[f"raw: {text[:300]!r}"],
        cost_usd=0.0, gate="bio_judge",
    )


# ──────────────────────────────────────────────────────────────────────────
# Combined verification
# ──────────────────────────────────────────────────────────────────────────


def _run_llm_gate(
    fn, args: tuple, gate_name: str,
) -> tuple[str, dict[str, Any]]:
    """Wrapper for running an LLM gate in a thread pool.
    Returns (gate_name, result_dict) so the caller can merge into gate_results.
    """
    try:
        r = fn(*args)
        return gate_name, r
    except Exception as exc:
        return gate_name, {
            "pass": False, "score": 0.0,
            "reason": f"gate crashed: {exc}", "issues": [str(exc)],
            "cost_usd": 0.0, "gate": gate_name,
        }


def verify_question(
    client: openai.OpenAI,
    question: dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> tuple[bool, dict[str, Any]]:
    """Run all applicable quality gates. Returns (passed, gate_results).

    Deterministic gates (calculator, sympy, chem_stoich) run sequentially —
    they are instant. LLM gates (solver, reviewer, bio_judge) run concurrently
    via ThreadPoolExecutor since they are independent of each other and
    the main bottleneck is I/O wait on z.ai responses.
    """
    module = str(question.get("module", "")).lower()
    gate_results: dict[str, Any] = {}

    # ── Phase 1: Deterministic gates (instant, sequential) ──
    # 1. Calculator check
    try:
        gate_results["calculator"] = calculator_check.check(question)
    except Exception as exc:
        gate_results["calculator"] = {
            "pass": False, "score": 0.0,
            "reason": f"gate crashed: {exc}", "issues": [str(exc)],
            "cost_usd": 0.0, "gate": "calculator",
        }

    # 2. SymPy verifier
    try:
        gate_results["sympy"] = sympy_verifier.check(question)
    except Exception as exc:
        gate_results["sympy"] = {
            "pass": False, "score": 0.0,
            "reason": f"gate crashed: {exc}", "issues": [str(exc)],
            "cost_usd": 0.0, "gate": "sympy",
        }

    # 3. Chemistry stoichiometry (chemistry only)
    if module == "chemistry":
        try:
            gate_results["chem_stoich"] = chem_stoich_check.check(question)
        except Exception as exc:
            gate_results["chem_stoich"] = {
                "pass": False, "score": 0.0,
                "reason": f"gate crashed: {exc}", "issues": [str(exc)],
                "cost_usd": 0.0, "gate": "chem_stoich",
            }

    # ── Phase 2: LLM gates (concurrent via thread pool) ──
    # Solver and reviewer always run. Bio judge runs for biology only.
    # These are pure I/O-bound waits on z.ai — perfect for threads.
    llm_tasks: list[tuple[str, Any, tuple]] = [
        ("solver", _solver_check_glm, (client, question)),
        ("reviewer", _reviewer_check_glm, (client, question)),
    ]
    if module == "biology":
        llm_tasks.append(
            ("bio_judge", _bio_judge_check_glm, (client, question)),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(llm_tasks)) as pool:
        futures = {
            pool.submit(_run_llm_gate, fn, args, name): name
            for name, fn, args in llm_tasks
        }
        for future in concurrent.futures.as_completed(futures):
            name, result = future.result()
            gate_results[name] = result

    # Determine overall pass: all non-skipped gates must pass.
    overall_pass = all(
        ("skipped" in v and v["skipped"]) or v.get("pass", False)
        for v in gate_results.values()
    )

    return overall_pass, gate_results


# ──────────────────────────────────────────────────────────────────────────
# Retry-with-feedback logic
# ──────────────────────────────────────────────────────────────────────────

# Gates whose failures are retryable (soft/gate-score issues).
# Anything NOT in this set is a hard error and will NOT trigger retries.
# calculator: GLM often generates non-integer/un-mental numbers;
#   revision with explicit feedback usually fixes it.
# calculability (ESA-55): the rebuilt-stack name for the same calculator-free
#   gate. We proved calculability false positives exist (distractor-rationale
#   scanning), so its rejections must be retryable — keep both spellings so
#   the set is correct whether this pipeline emits the legacy "calculator" key
#   or the rebuilt "calculability" key.
# sympy: left non-retryable — if the math is wrong, LLM revision rarely fixes the root cause.
RETRYABLE_GATES = {"solver", "reviewer", "bio_judge", "chem_stoich",
                   "calculator", "calculability"}

# Hard-failure indicators inside gate results — if any of these patterns
# appear in a gate's reason string, the failure is NOT retryable even if
# the gate name is in RETRYABLE_GATES.
_HARD_FAILURE_PATTERNS = [
    "gate crashed",
    "GLM call failed",
]


def _is_retryable(failed_gates: list[str], gate_results: dict[str, Any]) -> bool:
    """Decide whether a verification failure is eligible for revision retry.

    Rules:
    - If NO gates failed → not retryable (already passed).
    - If ANY failed gate is NOT in RETRYABLE_GATES → hard error, no retry.
      (This catches sympy failures, which mean the math answer is wrong.)
    - If ANY retryable gate's reason matches a hard-failure pattern
      (gate crashed, GLM call failed) → no retry.
    - Otherwise → retryable.
    """
    if not failed_gates:
        return False

    for gate_name in failed_gates:
        # Non-retryable gate name (e.g. sympy)
        if gate_name not in RETRYABLE_GATES:
            return False
        # Hard failure pattern inside a retryable gate
        reason = gate_results.get(gate_name, {}).get("reason", "")
        for pattern in _HARD_FAILURE_PATTERNS:
            if pattern.lower() in reason.lower():
                return False

    return True


REVISION_SYSTEM_PROMPT = """\
You are an expert ESAT question reviser. A previously generated ESAT \
multiple-choice question failed quality verification for specific reasons. \
Your task is to revise the question to fix ALL of the listed issues while \
keeping the same topic, difficulty, and general structure.

## RULES
- Return ONLY a corrected JSON object in the exact same format as the input.
- Do NOT change the spec_topic, module, or difficulty_band.
- Fix every issue listed in the failure reasons.
- Ensure the correct_answer is genuinely correct and the explanation derives it.
- Keep distractors plausible and tied to identifiable misconceptions.
- Output ONLY the JSON object. No prose before or after. No ``` fences.

## OUTPUT FORMAT (EXACT FIELD ORDER — every field is required)
```json
{
  "question_text": "...",
  "options": {"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."},
  "correct_answer": "<one of A,B,C,D,E>",
  "explanation": "<clean worked solution ending on the committed answer>",
  "distractor_analysis": {
    "<each wrong letter>": "<one-line misconception>"
  },
  "difficulty_band": "<Easy|Medium|Hard|Very Hard>",
  "difficulty_score": <1-5 integer>,
  "subject": "<specific topic name from the ESAT taxonomy>",
  "has_diagram": <true|false>,
  "diagram_description": "<if has_diagram is true, describe the diagram in detail; else empty string>"
}
```

## FIELD INSTRUCTIONS
- **difficulty_score**: integer 1-5 (1 = straightforward recall, 5 = multi-step synthesis). Carry over from the input if present and still accurate.
- **subject**: non-empty ESAT taxonomy topic name. Carry over from the input if present.
- **has_diagram** / **diagram_description**: set has_diagram true only if the question is unsolvable without a diagram, and describe it (labels, axes, key dimensions); otherwise false and an empty string.
- **distractor_analysis** MUST contain a one-line misconception for EVERY wrong option (never include the correct option as a key).

## NON-NEGOTIABLE EXAM CONVENTIONS
- Gravitational field strength: g = 10 N kg⁻¹ (ALWAYS).
- Angles: {0, 30, 45, 60, 90} degrees only.
- Arithmetic: doable without a calculator — integers, simple fractions, perfect roots, common surds. NO 3+ decimal places, no non-standard angles, no ugly multiplications.
- Exactly FIVE options (A–E); exactly ONE correct.

Output ONLY the JSON object. No prose before or after. No ``` fences.
"""


def _revise_question(
    client: openai.OpenAI,
    question: dict[str, Any],
    gate_results: dict[str, Any],
    failed_gates: list[str],
    model: str = DEFAULT_MODEL,
) -> tuple[dict[str, Any], int, int]:
    """Ask GLM-5.2 to revise a question based on verification failure reasons.

    Returns (revised_question_dict, input_tokens, output_tokens).
    Raises on parse/validation failure (caller should treat as hard error).
    """
    # Build failure reasons string
    failure_lines: list[str] = []
    for gate_name in failed_gates:
        reason = gate_results.get(gate_name, {}).get("reason", "unknown")
        issues = gate_results.get(gate_name, {}).get("issues", [])
        line = f"- {gate_name}: {reason}"
        if issues:
            line += f" (details: {'; '.join(str(i) for i in issues[:3])})"
        failure_lines.append(line)

    # Add explicit ESAT calculator-free instructions when calculator gate failed
    calculator_failed = any("calculator" in g for g in failed_gates)
    if calculator_failed:
        calc_issues = gate_results.get("calculator", {}).get("issues", [])
        failure_lines.append(
            "CALCULATOR-FREE REMINDER: ESAT is strictly non-calculator. "
            "You MUST use only: integers, simple fractions (1/2, 1/3, 1/4), "
            "perfect square roots (√4, √9, √16, √25), common surds (√2, √3, √5), "
            "standard trig angles (0°, 30°, 45°, 60°, 90°), and g = 10 N/kg. "
            "NO 3+ decimal places, no non-standard angles, no ugly multiplications. "
            f"Specific issues to fix: {'; '.join(str(i) for i in calc_issues[:5])}"
        )

    failure_text = "\n".join(failure_lines)

    # Strip internal/metadata fields from the question before sending.
    # Include the schema fields parse_question() requires so the model can
    # preserve/adjust them rather than omitting them and failing validation.
    revision_fields = {"question_text", "options", "correct_answer",
                       "explanation", "distractor_analysis", "difficulty_band",
                       "difficulty_score", "subject", "has_diagram",
                       "diagram_description"}
    clean_question = {k: v for k, v in question.items() if k in revision_fields}

    user_prompt = (
        f"## FAILED QUESTION (JSON)\n\n"
        f"{json.dumps(clean_question, indent=2, ensure_ascii=False)}\n\n"
        f"## FAILURE REASONS\n\n"
        f"{failure_text}\n\n"
        f"## TASK\n"
        f"Revise the question above to fix ALL listed failures. "
        f"Return the corrected JSON in the same format."
    )

    text, in_tok, out_tok = _glm_call(
        client, REVISION_SYSTEM_PROMPT, user_prompt,
        model=model, max_tokens=MAX_TOKENS,
    )

    revised = generator_glm.parse_question(text)

    # Carry forward metadata fields that the revision prompt doesn't produce
    for meta_key in ("module", "spec_topic", "source", "generated_from_template_id",
                      "prompt_hash", "model"):
        if meta_key in question and meta_key not in revised:
            revised[meta_key] = question[meta_key]
    if "difficulty" not in revised:
        revised["difficulty"] = revised.get("difficulty_band") or question.get("difficulty", "")

    # Re-attach distractor_analysis into metadata + explanation (same as generator)
    da = revised.get("distractor_analysis")
    if isinstance(da, dict) and da:
        meta = revised.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        meta["distractor_analysis"] = da
        revised["metadata"] = meta

        ca = revised.get("correct_answer", "")
        wrong_letters = [L for L in ("A", "B", "C", "D", "E") if L != ca]
        lines = [
            f"  - **{L}**: {da[L].strip()}"
            for L in wrong_letters
            if isinstance(da.get(L), str) and da[L].strip()
        ]
        if lines:
            revised["explanation"] = (
                revised["explanation"].rstrip()
                + "\n\n**Why the other options are wrong:**\n"
                + "\n".join(lines)
            )

    return revised, in_tok, out_tok


# ──────────────────────────────────────────────────────────────────────────
# Quota gating
# ──────────────────────────────────────────────────────────────────────────


def _format_duration(seconds: float) -> str:
    """Format seconds into a human-readable duration string."""
    s = int(seconds)
    if s >= 86400:
        return f'{s // 86400}d {(s % 86400) // 3600}h'
    if s >= 3600:
        return f'{s // 3600}h {(s % 3600) // 60}m'
    if s >= 60:
        return f'{s // 60}m'
    return f'{s}s'


def _fetch_quota() -> Optional[dict[str, Any]]:
    """Fetch quota from the local dashboard endpoint (pre-computed, correct values)."""
    try:
        with urllib.request.urlopen(_LOCAL_QUOTA_URL, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        logger.warning("Quota endpoint unreachable: %s", exc)
        return None


def _check_quota_allows() -> tuple[bool, Optional[str]]:
    """Check if both weekly and 5-hour windows are within budget.

    We only proceed when actual usage <= QUOTA_USAGE_MULTIPLIER * elapsed %.
    This ensures we don't burn quota faster than time passes.

    Returns (allowed, reason_string_or_None).
    """
    data = _fetch_quota()
    if data is None:
        return False, "quota endpoint unreachable"  # fail close

    for window_name in ("weekly", "fiveHour"):
        window = data.get(window_name, {})
        used = float(window.get("percentage", 0))
        elapsed = float(window.get("elapsedPct", 0))
        resets = window.get("resetsIn", "unknown")

        # Floor threshold: below these elapsed percentages, skip the 90% rule
        floor = FIVE_HOUR_FLOOR_PCT if window_name == "fiveHour" else WEEKLY_FLOOR_PCT
        if elapsed <= floor:
            logger.debug(
                "%s window below floor (%.1f%% <= %d%%), skipping quota check",
                window_name, elapsed, floor,
            )
            continue

        budget = math.floor(QUOTA_USAGE_MULTIPLIER * elapsed)
        if used > budget:
            return False, (
                f"{window_name}: {used:.1f}% used, "
                f"budget is {budget}% (elapsed {elapsed:.1f}% × {QUOTA_USAGE_MULTIPLIER}), "
                f"resets in {resets}"
            )

    return True, None


# ──────────────────────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────────────────────


def _get_dbconn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS questions (
          id              TEXT PRIMARY KEY,
          exam_type       TEXT NOT NULL,
          year            TEXT,
          paper           TEXT,
          module          TEXT,
          section         TEXT,
          subject         TEXT,
          part            TEXT,
          question_number INTEGER NOT NULL,
          question_text   TEXT NOT NULL,
          question_images TEXT DEFAULT '[]',
          options         TEXT NOT NULL,
          correct_answer  TEXT NOT NULL,
          explanation     TEXT DEFAULT '',
          explanation_images TEXT DEFAULT '[]',
          screenshot      TEXT DEFAULT '',
          enrichment      TEXT,
          metadata        TEXT DEFAULT '{}',
          source          TEXT NOT NULL DEFAULT 'corpus',
          generated_from_template_id TEXT,
          difficulty_score REAL,
          created_at      TEXT DEFAULT (datetime('now')),
          updated_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_q_exam ON questions(exam_type);
        CREATE INDEX IF NOT EXISTS idx_q_module ON questions(module);
        CREATE INDEX IF NOT EXISTS idx_q_source ON questions(source);

        CREATE TABLE IF NOT EXISTS attempt_stats (
          question_id     TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
          times_answered  INTEGER DEFAULT 0,
          times_correct   INTEGER DEFAULT 0,
          avg_time_ms     REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS generation_attempts (
          id              TEXT PRIMARY KEY,
          batch_id        TEXT NOT NULL,
          spec_topic      TEXT NOT NULL,
          model           TEXT NOT NULL,
          prompt_hash     TEXT,
          question_text   TEXT NOT NULL,
          options         TEXT NOT NULL,
          correct_answer  TEXT NOT NULL,
          explanation     TEXT DEFAULT '',
          status          TEXT NOT NULL DEFAULT 'pending',
          reject_reason   TEXT,
          question_id     TEXT,
          created_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ga_batch ON generation_attempts(batch_id);
        CREATE INDEX IF NOT EXISTS idx_ga_status ON generation_attempts(status);
        """
    )
    # Migration: add verification column if it doesn't exist
    try:
        conn.execute("ALTER TABLE generation_attempts ADD COLUMN verification TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.commit()


def _insert_question(
    conn: sqlite3.Connection,
    question: dict[str, Any],
    gen_result: generator_glm.GenResult,
    batch_id: str,
    verification: dict[str, Any],
) -> str:
    """Insert a verified question into both questions and generation_attempts."""
    qid = f"gen-glm-{uuid.uuid4().hex[:12]}"
    att_id = f"att-glm-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat(sep=" ", timespec="seconds")
    module = question.get("module", "")
    spec_topic = question.get("spec_topic", "")
    options_json = json.dumps(question.get("options", {}))
    metadata = question.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    metadata_json = json.dumps(metadata)

    conn.execute(
        """INSERT INTO questions (
            id, exam_type, year, paper, module, section, subject, part,
            question_number, question_text, question_images, options,
            correct_answer, explanation, explanation_images, screenshot,
            enrichment, metadata, source, generated_from_template_id,
            difficulty_score, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            qid, "esat", None, "ESAT", module, "", "", "", 0,
            question["question_text"], "[]", options_json,
            question["correct_answer"], question.get("explanation", ""),
            "[]", "", None, metadata_json, "generated",
            question.get("generated_from_template_id"), None, now, now,
        ),
    )

    conn.execute(
        """INSERT INTO generation_attempts (
            id, batch_id, spec_topic, model, prompt_hash,
            question_text, options, correct_answer, explanation,
            status, reject_reason, verification, question_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            att_id, batch_id, spec_topic, gen_result.model,
            question.get("prompt_hash"),
            question["question_text"], options_json,
            question["correct_answer"], question.get("explanation", ""),
            "accepted", None, json.dumps(verification), qid, now,
        ),
    )
    conn.commit()
    return qid


def _insert_rejected_attempt(
    conn: sqlite3.Connection,
    question: dict[str, Any],
    gen_result: generator_glm.GenResult,
    batch_id: str,
    verification: dict[str, Any],
    failed_gates: list[str],
) -> None:
    """Record a rejected generation attempt."""
    att_id = f"att-glm-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat(sep=" ", timespec="seconds")
    options_json = json.dumps(question.get("options", {}))

    conn.execute(
        """INSERT INTO generation_attempts (
            id, batch_id, spec_topic, model, prompt_hash,
            question_text, options, correct_answer, explanation,
            status, reject_reason, question_id, verification, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            att_id, batch_id, question.get("spec_topic", ""),
            gen_result.model, question.get("prompt_hash"),
            question["question_text"], options_json,
            question["correct_answer"], question.get("explanation", ""),
            "rejected", f"failed gates: {', '.join(failed_gates)}",
            None,
            json.dumps(verification), now,
        ),
    )
    conn.commit()


# ──────────────────────────────────────────────────────────────────────────
# Work queue
# ──────────────────────────────────────────────────────────────────────────


def _build_work_queue() -> list[tuple[str, str]]:
    specs = generator_glm.discover_specs(PATTERNS_DIR)
    if not specs:
        logger.error("No complete pattern bundles found in %s", PATTERNS_DIR)
        return []
    queue = [(s, d) for s in specs for d in VALID_DIFFICULTIES]
    random.shuffle(queue)
    return queue


# ──────────────────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────────────
# PID-based lock to prevent concurrent runs
# ──────────────────────────────────────────────────────────────────────────


def _acquire_lock() -> bool:
    """Try to acquire the lock file. Returns True if lock acquired.
    Returns False if another instance is already running.
    """
    try:
        if LOCK_FILE.exists():
            # Read existing PID
            old_pid = LOCK_FILE.read_text().strip()
            if old_pid:
                # Check if the process is still alive
                try:
                    os.kill(int(old_pid), 0)  # signal 0 = check existence
                    # Process exists — we cannot acquire the lock
                    logger.info(
                        "Another instance is running (PID %s). Exiting.",
                        old_pid,
                    )
                    return False
                except ProcessLookupError:
                    # Stale lock — process is gone, remove it
                    logger.info(
                        "Stale lock from PID %s (process gone). Replacing.",
                        old_pid,
                    )
                    LOCK_FILE.unlink()
                except ValueError:
                    # Corrupt PID — remove it
                    logger.warning("Corrupt lock file. Replacing.")
                    LOCK_FILE.unlink()
                except PermissionError:
                    logger.warning(
                        "Cannot signal PID %s (permission denied). Assuming stale.",
                        old_pid,
                    )
                    LOCK_FILE.unlink()

        # Write our PID
        LOCK_FILE.write_text(str(os.getpid()))
        return True
    except OSError as exc:
        logger.warning("Could not acquire lock: %s", exc)
        return False


def _release_lock() -> None:
    """Remove the lock file."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except OSError:
        pass



def run(
    *,
    client: Optional[openai.OpenAI] = None,
    max_questions: Optional[int] = None,
    spec_code: Optional[str] = None,
    difficulty: Optional[str] = None,
    dry_run: bool = False,
    no_wait: bool = False,
    max_runtime_s: float = 0.0,
) -> int:
    """Main generate-then-verify loop. Returns count of verified questions inserted."""

    # ── Build work queue ──
    if spec_code and difficulty:
        queue = [(spec_code, difficulty)]
    else:
        queue = _build_work_queue()

    if not queue:
        logger.error("No work to do.")
        return 0

    logger.info("Queue: %d (spec, difficulty) combos", len(queue))

    if dry_run:
        print(f"\nDry run — {len(queue)} combos queued:")
        for sc, diff in queue[:10]:
            print(f"  {sc} / {diff}")
        if len(queue) > 10:
            print(f"  ... ({len(queue)} total)")
        print(f"\nGates per question: calculator, sympy, solver (GLM-5.2), reviewer (GLM-5.2)")
        print(f"  + chem_stoich (chemistry only) + bio_judge (biology only, GLM-5.2)")
        print(f"Quota rule: usage <= {QUOTA_USAGE_MULTIPLIER} x elapsed %")
        if max_runtime_s > 0:
            print(f"Max runtime: {_format_duration(max_runtime_s)}")
        return 0

    # ── Acquire PID lock (prevent concurrent runs from overlapping cron) ──
    if not _acquire_lock():
        logger.info("Could not acquire lock — another instance is running.")
        return 0

    try:
        return _run_locked(
            client=client,
            max_questions=max_questions,
            queue=queue,
            no_wait=no_wait,
            max_runtime_s=max_runtime_s,
        )
    finally:
        _release_lock()


def _run_locked(
    *,
    client: openai.OpenAI,
    max_questions: Optional[int],
    queue: list[tuple[str, str]],
    no_wait: bool,
    max_runtime_s: float,
) -> int:
    """Inner loop — only called while holding the PID lock."""

    # ── Pre-flight quota check (for cron / no-wait mode) ──
    if no_wait:
        pre_allowed, pre_info = _check_quota_allows()
        if not pre_allowed:
            logger.info(
                "Pre-flight: over budget — exiting (cron will retry). %s",
                pre_info,
            )
            return 0

    # ── Start runtime clock ──
    global _start_time, _max_runtime_s
    _start_time = time.monotonic()
    _max_runtime_s = max_runtime_s
    if max_runtime_s > 0:
        logger.info("Max runtime: %s", _format_duration(max_runtime_s))

    # ── Ensure DB exists ──
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _get_dbconn()
    _init_db(conn)

    batch_id = f"glm-gv-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    stats = {
        "total_generated": 0,
        "total_passed": 0,
        "total_failed": 0,
        "total_revised": 0,
        "total_accepted_on_revision": 0,
        "gate_failures": {},  # gate_name -> count
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "errors": 0,
    }

    queue_idx = 0
    while True:
        if _shutdown:
            logger.info("Graceful shutdown requested.")
            break

        if max_questions is not None and stats["total_passed"] >= max_questions:
            logger.info("Reached --max=%d verified questions.", max_questions)
            break

        # Max runtime check
        if _max_runtime_s > 0 and (time.monotonic() - _start_time) >= _max_runtime_s:
            logger.info("Reached max runtime (%s).", _format_duration(_max_runtime_s))
            break

        # If queue exhausted, reshuffle for another pass
        if queue_idx >= len(queue):
            logger.info("Queue exhausted — reshuffling for another pass.")
            random.shuffle(queue)
            queue_idx = 0

        # Quota check BEFORE generation
        allowed, reset_info = _check_quota_allows()
        if not allowed:
            logger.info("Quota guard: %s", reset_info)
            logger.info("Quota exhausted — exiting (cron will retry).")
            break

        sc, diff = queue[queue_idx]
        queue_idx += 1

        seed = random.randint(1, 2**31)
        stats["total_generated"] += 1

        try:
            # Generate
            question, gen_result = generator_glm.generate(
                client, sc, diff, seed=seed, patterns_dir=PATTERNS_DIR,
            )
            stats["total_input_tokens"] += gen_result.input_tokens
            stats["total_output_tokens"] += gen_result.output_tokens

        except Exception as exc:
            stats["errors"] += 1
            logger.error(
                "Generation failed for %s/%s: %s: %s",
                sc, diff, type(exc).__name__, exc,
            )
            continue

        # Verify
        try:
            passed, gate_results = verify_question(client, question, model=DEFAULT_MODEL)
        except Exception as exc:
            stats["errors"] += 1
            logger.error(
                "Verification crashed for %s/%s: %s: %s",
                sc, diff, type(exc).__name__, exc,
            )
            continue

        failed_gates = [
            name for name, result in gate_results.items()
            if not result.get("pass", False)
        ]

        if passed:
            # ── Accepted on first attempt ──
            qid = _insert_question(conn, question, gen_result, batch_id, gate_results)
            stats["total_passed"] += 1
            logger.info(
                "✓ %s/%s → %s (passed all %d gates)",
                sc, diff, qid, len(gate_results),
            )
        elif _is_retryable(failed_gates, gate_results):
            # ── Retry-with-feedback loop ──
            revised = question
            retry_passed = False
            for attempt in range(1, MAX_REVISION_RETRIES + 1):
                logger.info(
                    "↻ %s/%s — revision attempt %d/%d (failed: %s)",
                    sc, diff, attempt, MAX_REVISION_RETRIES,
                    ", ".join(failed_gates),
                )
                try:
                    revised, rev_in, rev_out = _revise_question(
                        client, revised, gate_results, failed_gates,
                        model=DEFAULT_MODEL,
                    )
                    stats["total_input_tokens"] += rev_in
                    stats["total_output_tokens"] += rev_out
                    stats["total_revised"] += 1
                except Exception as exc:
                    logger.warning(
                        "↻ %s/%s — revision %d failed to parse: %s",
                        sc, diff, attempt, exc,
                    )
                    break

                # Re-verify the revision (all gates)
                try:
                    rev_passed, gate_results = verify_question(
                        client, revised, model=DEFAULT_MODEL,
                    )
                except Exception as exc:
                    logger.warning(
                        "↻ %s/%s — verification of revision %d crashed: %s",
                        sc, diff, attempt, exc,
                    )
                    continue

                if rev_passed:
                    # Build a minimal GenResult for the revision
                    rev_gen_result = generator_glm.GenResult(
                        text="revision",
                        model=DEFAULT_MODEL,
                        cost_usd=0.0,
                        input_tokens=0,
                        output_tokens=0,
                    )
                    qid = _insert_question(
                        conn, revised, rev_gen_result, batch_id, gate_results,
                    )
                    stats["total_passed"] += 1
                    stats["total_accepted_on_revision"] += 1
                    logger.info(
                        "✓ %s/%s → %s (passed on revision %d/%d)",
                        sc, diff, qid, attempt, MAX_REVISION_RETRIES,
                    )
                    retry_passed = True
                    break
                else:
                    failed_gates = [
                        name for name, result in gate_results.items()
                        if not result.get("pass", False)
                    ]
                    # Stop retrying if it's no longer retryable
                    if not _is_retryable(failed_gates, gate_results):
                        logger.info(
                            "↻ %s/%s — revision %d hit non-retryable failure, stopping",
                            sc, diff, attempt,
                        )
                        break
                    logger.info(
                        "↻ %s/%s — revision %d still failed: %s",
                        sc, diff, attempt,
                        ", ".join(failed_gates),
                    )

            if not retry_passed:
                # All retries exhausted — reject
                for name in failed_gates:
                    stats["gate_failures"][name] = stats["gate_failures"].get(name, 0) + 1
                final_gen_result = gen_result  # use original gen_result for the reject record
                _insert_rejected_attempt(
                    conn, revised, final_gen_result, batch_id, gate_results, failed_gates,
                )
                stats["total_failed"] += 1
                reasons = "; ".join(
                    f"{name}({gate_results[name].get('reason', '?')[:80]})"
                    for name in failed_gates
                )
                logger.info(
                    "✗ %s/%s — failed after %d revisions: %s",
                    sc, diff, MAX_REVISION_RETRIES, reasons,
                )
        else:
            # ── Non-retryable failure — reject immediately ──
            for name in failed_gates:
                stats["gate_failures"][name] = stats["gate_failures"].get(name, 0) + 1
            _insert_rejected_attempt(conn, question, gen_result, batch_id, gate_results, failed_gates)
            stats["total_failed"] += 1
            reasons = "; ".join(
                f"{name}({gate_results[name].get('reason', '?')[:80]})"
                for name in failed_gates
            )
            logger.info(
                "✗ %s/%s — hard failure, no retry: %s", sc, diff, reasons,
            )

        # Log progress every 10 generated
        total = stats["total_generated"]
        if total % 10 == 0:
            rate = (
                f"{stats['total_passed']/total*100:.1f}%"
                if total > 0 else "N/A"
            )
            allowed, _ = _check_quota_allows()
            headroom_info = "N/A (endpoint down)" if allowed else "LOW"
            logger.info(
                "[Progress] generated=%d passed=%d failed=%d rate=%s | "
                "tokens=%d+%d | quota_headroom=%s",
                total, stats["total_passed"], stats["total_failed"],
                rate, stats["total_input_tokens"], stats["total_output_tokens"],
                headroom_info,
            )

        # Minimal delay between questions (verification gates are now concurrent)
        time.sleep(0.3)

    conn.close()

    # ── Final summary ──
    total = stats["total_generated"]
    passed = stats["total_passed"]
    failed = stats["total_failed"]
    rate = f"{passed/total*100:.1f}%" if total > 0 else "N/A"

    logger.info("=" * 60)
    logger.info("GENERATE-AND-VERIFY COMPLETE: %s", batch_id)
    logger.info("  Total generated:  %d", total)
    logger.info("  Passed verification: %d", passed)
    logger.info("  Failed verification: %d", failed)
    logger.info("  Pass rate: %s", rate)
    logger.info("  Total revised: %d (accepted on revision: %d)",
                stats["total_revised"], stats["total_accepted_on_revision"])
    logger.info("  Errors: %d", stats["errors"])
    logger.info("  Total tokens: %d input + %d output",
                stats["total_input_tokens"], stats["total_output_tokens"])
    if stats["gate_failures"]:
        logger.info("  Per-gate failures:")
        for gate_name, count in sorted(
            stats["gate_failures"].items(), key=lambda x: -x[1]
        ):
            logger.info("    %s: %d", gate_name, count)
    logger.info("=" * 60)

    return passed

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="GLM-5.2 generate-then-verify with quota gating (ESA-41)",
    )
    p.add_argument("--spec-code", help="e.g. PHYS.P1 (for single question)")
    p.add_argument("--difficulty", choices=VALID_DIFFICULTIES, help="Easy, Medium, or Hard")
    p.add_argument("--max", type=int, default=None, help="Stop after N verified questions")
    p.add_argument("--dry-run", action="store_true", help="Show plan, don't call API")
    p.add_argument("--no-wait", action="store_true",
                    help="Exit immediately if quota exhausted (for cron use)")
    p.add_argument("--max-runtime", type=int, default=0,
                    help="Max wall-clock seconds before stopping (0 = no limit)")
    p.add_argument("--api-key", help="z.ai API key (or set ZAI_API_KEY env var)")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL})")
    p.add_argument("--patterns-dir", type=Path, default=PATTERNS_DIR)
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.dry_run:
        return run(
            dry_run=True,
            spec_code=args.spec_code,
            difficulty=args.difficulty,
            max_runtime_s=args.max_runtime,
        )

    # Resolve API key
    api_key = generator_glm.resolve_api_key(args.api_key)
    if not api_key:
        print(
            "ERROR: z.ai API key required. Set ZAI_API_KEY, pass --api-key, "
            "or install the OpenClaw z.ai plugin.",
            file=sys.stderr,
        )
        return 1

    client = openai.OpenAI(api_key=api_key, base_url=ZAI_BASE_URL)

    count = run(
        client=client,
        max_questions=args.max,
        spec_code=args.spec_code,
        difficulty=args.difficulty,
        no_wait=args.no_wait,
        max_runtime_s=args.max_runtime,
    )
    print(f"\nDone. {count} verified questions inserted into DB.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
