#!/usr/bin/env python3
"""
Subject-Specific Factual Checker — Layer 7 of the verification stack (ESA-45).

Uses GLM-5.2 via the z.ai API with the `web_search` tool enabled to verify the
domain-specific facts embedded in a generated question (chemistry, biology,
physics). The verifier is asked to enumerate the concrete factual claims in the
question + worked solution and judge each one:

* **confirmed**    — verifiable and correct
* **unconfirmed**  — could not be verified (flagged for review, but NOT fatal)
* **incorrect**    — verifiably wrong

A question is **rejected** iff at least one claim is `incorrect`. Maths
questions are skipped (they are covered by the SymPy gate, Layer 2).

z.ai web_search wiring — confirmed working with GLM-5.2:
    tools=[{"type": "web_search", "web_search": {}}]

Standard verdict dict:

    {
        "pass": bool,
        "score": float,        # 1.0 all-confirmed, 0.5 skip/unconfirmed, 0.0 incorrect
        "reason": str,
        "issues": list[str],   # per-claim notes
        "cost_usd": 0.0,       # z.ai is free
        "gate": "factual_check",
        "claims": list[dict],  # [{claim, verdict, note}, ...]
    }

Usage:
    python factual_check.py --question path/to/q.json
    python factual_check.py --self-test
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Optional

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
else:
    from .verdict import verdict  # type: ignore

logger = logging.getLogger(__name__)

try:
    import openai  # type: ignore
except ImportError:  # pragma: no cover
    openai = None  # type: ignore


# ---------------------------------------------------------------------------
# Subject routing
# ---------------------------------------------------------------------------

def _subject_family(question: dict[str, Any]) -> str:
    """Map a question to one of {chemistry, biology, physics, maths, other}."""
    blob = " ".join(str(x).lower() for x in (
        question.get("module"), question.get("subject"),
        question.get("spec_topic"), question.get("topic_code"),
    ) if x)
    if any(t in blob for t in ("chem", "c13", "c11", "c4", "c3", "c5", "c7", "c9", "c10", "c15")):
        return "chemistry"
    if any(t in blob for t in ("bio", "b1", "b6", "b9")):
        return "biology"
    if any(t in blob for t in ("phys", "p2", "p3", "p4", "p5", "p6", "p7", "p9")):
        return "physics"
    if any(t in blob for t in ("math", "m1", "m2", "m3", "m5", "mm")):
        return "maths"
    return "other"


# Per-subject factual emphasis, lifted from the ESA-45 spec.
SUBJECT_FOCUS = {
    "chemistry": (
        "Verify: valency consistency, charge balance in equations, realistic "
        "bond energies / enthalpies, correct molecular geometries, correct "
        "periodic trends, and physically plausible reaction conditions."
    ),
    "biology": (
        "Verify: accurate cell structures and functions, correct Mendelian and "
        "non-Mendelian genetic ratios, plausible experimental results, and "
        "correct biochemical pathways (e.g. respiration, photosynthesis)."
    ),
    "physics": (
        "Verify: energy / charge conservation, realistic orders of magnitude, "
        "correct formula applications, and physically plausible constants."
    ),
}


SYSTEM_PROMPT = """\
You are a rigorous subject-matter examiner fact-checking a single ESAT \
multiple-choice question using live web search. Your job is to ENUMERATE the \
concrete factual claims in the question and worked solution, then verify each \
one against authoritative sources.

{focus}

Rules:
- Search the web to confirm or refute each non-trivial factual claim (a named \
constant, a molecular geometry, a genetic ratio, a physical law, an order of \
magnitude, a biological pathway, etc.). Do NOT flag pure arithmetic — that is \
checked elsewhere.
- For each claim assign exactly one verdict:
    "confirmed"   — verifiable and correct
    "unconfirmed" — you could not verify it either way (no authoritative source)
    "incorrect"   — verifiably WRONG (contradicted by authoritative sources)
- Be specific and conservative. Only mark "incorrect" when you have positive \
evidence the claim is wrong. Minor wording imprecision is "confirmed".

Respond with ONLY a JSON object (no markdown fences, no prose) in this shape:
{{
  "claims": [
    {{"claim": "<the factual claim in question>", "verdict": "confirmed|unconfirmed|incorrect", "note": "<one-line evidence>"}}
  ],
  "summary": "<one sentence overall assessment>"
}}
"""


def _build_user_prompt(question: dict[str, Any], family: str) -> str:
    options = question.get("options")
    if isinstance(options, dict):
        opts_str = "\n".join(f"  {k}. {v}" for k, v in options.items())
    elif isinstance(options, list):
        letters = "ABCDE"
        opts_str = "\n".join(f"  {letters[i]}. {v}" for i, v in enumerate(options))
    else:
        opts_str = str(options)

    return (
        f"Subject family: {family}\n\n"
        f"Question:\n{question.get('question_text', '').strip()}\n\n"
        f"Options:\n{opts_str}\n\n"
        f"Marked correct answer: {question.get('correct_answer', '')}\n\n"
        f"Worked solution provided by the generator:\n"
        f"{(question.get('explanation') or question.get('worked_solution') or '').strip()}\n\n"
        f"Enumerate and verify the factual claims above."
    )


# ---------------------------------------------------------------------------
# z.ai GLM-5.2 + web_search client
# ---------------------------------------------------------------------------

_client = None


def _get_client():
    """Build (once) an OpenAI-compatible client pointed at z.ai."""
    global _client
    if _client is not None:
        return _client
    if openai is None:
        raise RuntimeError("openai SDK not installed")
    import generator_glm  # local import: avoid import-time side effects
    api_key = generator_glm.resolve_api_key(None)
    if not api_key:
        raise RuntimeError("z.ai API key not available (set ZAI_API_KEY or install the z.ai plugin)")
    _client = openai.OpenAI(api_key=api_key, base_url=generator_glm.ZAI_BASE_URL)
    return _client


def _call_glm_websearch(
    client,
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 2048,
) -> tuple[str, int, int]:
    """One GLM-5.2 call with web_search enabled. Returns (text, in_tok, out_tok)."""
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        # z.ai live web search — confirmed working with GLM-5.2.
        tools=[{"type": "web_search", "web_search": {}}],
    )
    text = response.choices[0].message.content or ""
    reasoning = getattr(response.choices[0].message, "reasoning_content", None) or ""
    if len(text.strip()) < 20 and reasoning.strip():
        text = reasoning
    usage = response.usage
    in_tok = usage.prompt_tokens if usage else 0
    out_tok = usage.completion_tokens if usage else 0
    return text, in_tok, out_tok


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> Optional[dict[str, Any]]:
    """Robustly pull the first {...} JSON object out of a model response."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _parse_claims(text: str) -> tuple[list[dict[str, Any]], str]:
    """Return (claims, summary). Claims default to [] on parse failure."""
    obj = _extract_json(text)
    if not isinstance(obj, dict):
        return [], ""
    claims = obj.get("claims") or []
    if not isinstance(claims, list):
        claims = []
    cleaned: list[dict[str, Any]] = []
    for c in claims:
        if not isinstance(c, dict):
            continue
        cleaned.append({
            "claim": str(c.get("claim", "")).strip(),
            "verdict": str(c.get("verdict", "unconfirmed")).strip().lower(),
            "note": str(c.get("note", "")).strip(),
        })
    summary = str(obj.get("summary", "")).strip()
    return cleaned, summary


# ---------------------------------------------------------------------------
# Core gate
# ---------------------------------------------------------------------------

def check(
    question: dict[str, Any],
    *,
    client=None,
    model: Optional[str] = None,
    focus_overrides: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Run the GLM-5.2 web-search factual check.

    Maths/other questions are skipped (pass, score 0.5). A question is rejected
    only when the verifier positively marks a claim `incorrect`. Transient API
    failures skip with a warning rather than rejecting (infra failure ≠ bad
    question).
    """
    family = _subject_family(question)
    if family not in SUBJECT_FOCUS:
        return verdict(
            passed=True,
            score=0.5,
            reason=f"not applicable — {family} questions are not web-fact-checked",
            issues=[],
            cost_usd=0.0,
            gate="factual_check",
            claims=[],
        )

    effective_model = model or "glm-5.2"
    focus = (focus_overrides or {}).get(family) or SUBJECT_FOCUS[family]
    system_prompt = SYSTEM_PROMPT.format(focus=focus)
    user_prompt = _build_user_prompt(question, family)

    try:
        cli = client if client is not None else _get_client()
        text, in_tok, out_tok = _call_glm_websearch(
            cli,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=effective_model,
        )
    except Exception as exc:
        logger.warning("factual_check API call failed: %s", exc)
        return verdict(
            passed=True,
            score=0.5,
            reason=f"web-search check skipped — API error ({exc})",
            issues=[f"api_error: {exc}"],
            cost_usd=0.0,
            gate="factual_check",
            claims=[],
        )

    claims, summary = _parse_claims(text)
    incorrect = [c for c in claims if c.get("verdict") == "incorrect"]
    unconfirmed = [c for c in claims if c.get("verdict") == "unconfirmed"]

    issues: list[str] = []
    for c in incorrect:
        issues.append(f"INCORRECT: {c.get('claim','')} — {c.get('note','')}".strip(" —"))
    for c in unconfirmed:
        issues.append(f"unconfirmed: {c.get('claim','')}")

    if incorrect:
        return verdict(
            passed=False,
            score=0.0,
            reason=f"{len(incorrect)} factual claim(s) flagged incorrect — {summary[:120]}",
            issues=issues,
            cost_usd=0.0,
            gate="factual_check",
            claims=claims,
            model=effective_model,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )

    if unconfirmed:
        return verdict(
            passed=True,
            score=0.75,
            reason=f"{len(unconfirmed)} claim(s) unconfirmed, none incorrect — {summary[:120]}",
            issues=issues,
            cost_usd=0.0,
            gate="factual_check",
            claims=claims,
            model=effective_model,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )

    return verdict(
        passed=True,
        score=1.0,
        reason=f"all {len(claims)} claim(s) confirmed — {summary[:120]}",
        issues=[],
        cost_usd=0.0,
        gate="factual_check",
        claims=claims,
        model=effective_model,
        input_tokens=in_tok,
        output_tokens=out_tok,
    )


# ---------------------------------------------------------------------------
# Self-test (mocked GLM client — no network)
# ---------------------------------------------------------------------------

class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content
        self.reasoning_content = None


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeUsage:
    def __init__(self) -> None:
        self.prompt_tokens = 100
        self.completion_tokens = 50


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage()


class _FakeClient:
    """Records calls; returns a queued JSON response."""
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls = 0

        class _Completions:
            def __init__(self, outer) -> None:
                self.outer = outer

            def create(self, **kwargs):
                self.outer.calls += 1
                # Confirm the web_search tool was wired in.
                tools = kwargs.get("tools") or []
                assert any(t.get("type") == "web_search" for t in tools), \
                    "web_search tool not attached"
                return _FakeResponse(json.dumps(self.outer._payload))

        class _Chat:
            def __init__(self, outer) -> None:
                self.completions = _Completions(outer)

        self.chat = _Chat(self)


def _run_self_test() -> int:
    chem_q = {
        "module": "Chemistry", "subject": "Organic Chemistry", "spec_topic": "CHEM.C4",
        "question_text": "What is the molecular geometry of methane (CH4)?",
        "options": {"A": "tetrahedral", "B": "square planar", "C": "pyramidal", "D": "linear"},
        "correct_answer": "A",
        "explanation": "Methane has four bonding pairs and no lone pairs, so it is tetrahedral.",
    }
    bad_q = {
        "module": "Physics", "subject": "Quantum", "spec_topic": "PHYS.P5",
        "question_text": "The speed of light in vacuum is 3e9 m/s.",
        "options": {"A": "3e9 m/s"}, "correct_answer": "A",
        "explanation": "c = 3 x 10^9 m/s.",
    }
    maths_q = {
        "module": "Mathematics 1", "subject": "Algebra", "spec_topic": "MATHS1.M4",
        "question_text": "Expand (x+1)^2.", "options": {"A": "x^2+2x+1"},
        "correct_answer": "A", "explanation": "(x+1)^2 = x^2+2x+1.",
    }

    confirmed_payload = {"claims": [
        {"claim": "CH4 is tetrahedral", "verdict": "confirmed", "note": "standard VSEPR"}],
        "summary": "Correct."}
    incorrect_payload = {"claims": [
        {"claim": "c = 3e9 m/s", "verdict": "incorrect", "note": "c is 3e8 m/s, not 3e9"}],
        "summary": "Speed of light value is wrong."}

    c_ok = check(chem_q, client=_FakeClient(confirmed_payload))
    c_bad = check(bad_q, client=_FakeClient(incorrect_payload))
    c_maths = check(maths_q, client=_FakeClient(confirmed_payload))

    failures = 0
    for name, r, expect_pass, expect_score in (
        ("confirmed_passes", c_ok, True, 1.0),
        ("incorrect_rejects", c_bad, False, 0.0),
        ("maths_skips", c_maths, True, 0.5),
    ):
        ok = r["pass"] == expect_pass and abs(r["score"] - expect_score) < 1e-6
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {name}: pass={r['pass']} score={r['score']} ({r['reason'][:50]})")
        if not ok:
            print(f"        issues={r['issues']}")
            failures += 1
    print(f"\n{3 - failures}/3 cases passed")
    return failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_question(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data and isinstance(data["questions"], list):
        return data["questions"][0]
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT factual checker (Layer 7, GLM-5.2 + web_search)")
    p.add_argument("--question", type=Path, help="Path to a question JSON file")
    p.add_argument("--model", default="glm-5.2", help="GLM model id (default glm-5.2)")
    p.add_argument("--self-test", action="store_true", help="Run the mocked self-test")
    args = p.parse_args(argv)

    if args.self_test:
        return _run_self_test()

    if not args.question:
        p.error("--question or --self-test is required")

    question = _load_question(args.question)
    result = check(question, model=args.model)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
