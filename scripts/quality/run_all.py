#!/usr/bin/env python3
"""
End-to-end runner for the rebuilt ESA-45 verification stack (Layers 1-5 + 7).

Runs every applicable gate over a single generated question in the spec order
(fast reject-first → slow always-on), short-circuiting on the first gate that
returns a hard reject so we don't pay for expensive LLM calls on a question
that's already discarded:

    1. calculability       — Layer 1, rule-based (Tier 1 reject)
    2. dedup_check          — Layer 5, FAISS near-duplicate + concept cap
    3. sympy_verify         — Layer 2, symbolic solve-and-compare
    4. solver               — Layer 3, 3× independent LLM solve + majority vote
    5. structural_difficulty— Layer 4, deterministic 6-feature scorer (always passes)
    6. factual_check        — Layer 7, GLM-5.2 + web_search domain facts

A question is accepted iff every gate passes (skipped gates don't count). The
structural difficulty score is surfaced at the top level so the caller
(nightly_run) can store it on the question record alongside the LLM
self-assessment.

Usage:
    python run_all.py --question path/to/q.json
    python run_all.py --question q.json --skip-gates solver,factual_check
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import calculability  # type: ignore
    import dedup_check  # type: ignore
    import sympy_verify  # type: ignore
    import solver  # type: ignore
    import structural_difficulty  # type: ignore
    import factual_check  # type: ignore
else:
    from . import (  # type: ignore
        calculability,
        dedup_check,
        sympy_verify,
        solver,
        structural_difficulty,
        factual_check,
    )

# Per-question cost ceiling (informational). The rebuilt stack runs on free
# tiers (Gemini free for solver, z.ai free for factual_check), so this rarely
# trips; it is kept as a runaway-cost guard.
COST_BUDGET_USD = 0.02


@dataclass
class GateContext:
    """Optional pre-loaded resources shared across one batch's gates.

    Building the FAISS index (~8s) and the GLM client once per batch — instead
    of per question — is a large speed-up. Any field may be None, in which case
    the owning gate lazy-loads its own resource.
    """
    db_path: Optional[Path] = None
    dedup_index: Optional["dedup_check.DedupIndex"] = None
    glm_client: Any = None
    solver_model: Optional[str] = None


def _gate_calculability(question, ctx: GateContext):
    return calculability.check(question)


def _gate_dedup(question, ctx: GateContext):
    kwargs: dict[str, Any] = {}
    if ctx.dedup_index is not None:
        kwargs["index"] = ctx.dedup_index
    if ctx.db_path is not None:
        kwargs["db_path"] = ctx.db_path
    return dedup_check.check(question, **kwargs)


def _gate_sympy(question, ctx: GateContext):
    return sympy_verify.check(question)


def _gate_solver(question, ctx: GateContext):
    if ctx.solver_model:
        return solver.check(question, model=ctx.solver_model)
    return solver.check(question)


def _gate_structural(question, ctx: GateContext):
    return structural_difficulty.check(question)


def _gate_factual(question, ctx: GateContext):
    if ctx.glm_client is not None:
        return factual_check.check(question, client=ctx.glm_client)
    return factual_check.check(question)


# (key, label, runner). Order = spec execution order (cheap reject-first).
GATES: list[tuple[str, str, Any]] = [
    ("calculability", "Layer 1: Calculability Checker", _gate_calculability),
    ("dedup_check", "Layer 5: FAISS Dedup + Concept Cap", _gate_dedup),
    ("sympy_verify", "Layer 2: SymPy Solution Verifier", _gate_sympy),
    ("solver", "Layer 3: LLM Solver (3× majority vote)", _gate_solver),
    ("structural_difficulty", "Layer 4: Structural Difficulty Scorer", _gate_structural),
    ("factual_check", "Layer 7: Factual Check (GLM-5.2 + web_search)", _gate_factual),
]


def run_all(
    question: dict[str, Any],
    *,
    skip: Optional[set[str]] = None,
    ctx: Optional[GateContext] = None,
    short_circuit: bool = True,
) -> dict[str, Any]:
    """Run every applicable gate over a single question.

    Args:
        question: the generated question dict (corpus-schema keys).
        skip: gate keys to skip (e.g. {"solver", "factual_check"} for a fast
            dry-check). Skipped gates are marked and never reject.
        ctx: pre-loaded shared resources. If None, an empty context is used and
            each gate lazy-loads what it needs.
        short_circuit: stop at the first hard-reject gate. On, by default, to
            avoid paying for solver/factual on already-discarded questions.
    """
    skip = skip or set()
    ctx = ctx or GateContext()

    results: dict[str, Any] = {}
    total_cost = 0.0
    rejected = False

    for key, label, runner in GATES:
        if key in skip:
            results[key] = {"skipped": True, "label": label}
            continue
        try:
            r = runner(question, ctx)
        except Exception as exc:
            # A crashing gate is a soft skip (don't poison the whole stack),
            # but recorded as a failure so it is visible.
            r = {
                "pass": False,
                "score": 0.0,
                "reason": f"gate crashed: {exc}",
                "issues": [str(exc)],
                "cost_usd": 0.0,
            }
        results[key] = {"label": label, "skipped": False, **r}
        total_cost += r.get("cost_usd", 0.0) or 0.0

        if short_circuit and not r.get("pass", False):
            rejected = True
            break

    overall_pass = not rejected and all(
        (v.get("skipped") or v.get("pass"))
        for v in results.values()
    )

    # Surface the structural score for the caller to persist.
    structural_score = None
    sd = results.get("structural_difficulty")
    if isinstance(sd, dict) and not sd.get("skipped"):
        structural_score = sd.get("difficulty_score_structural")

    return {
        "pass": overall_pass,
        "total_cost_usd": round(total_cost, 6),
        "within_budget": total_cost <= COST_BUDGET_USD,
        "budget_usd": COST_BUDGET_USD,
        "gates": results,
        "difficulty_score_structural": structural_score,
    }


def _load_question(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data and isinstance(data["questions"], list):
        return data["questions"][0]
    return data


def main(argv: list[str] | None = None) -> int:
    all_keys = ",".join(k for k, _, _ in GATES)
    p = argparse.ArgumentParser(description="Run the rebuilt ESA-45 verification stack")
    p.add_argument("--question", type=Path, required=True)
    p.add_argument(
        "--skip-gates",
        default="",
        help=f"Comma-separated gate keys to skip ({all_keys})",
    )
    args = p.parse_args(argv)

    skip = {s.strip() for s in args.skip_gates.split(",") if s.strip()}
    question = _load_question(args.question)
    summary = run_all(question, skip=skip)

    print(json.dumps(summary, indent=2))
    return 0 if (summary["pass"] and summary["within_budget"]) else 1


if __name__ == "__main__":
    sys.exit(main())
