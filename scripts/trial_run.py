#!/usr/bin/env python3
"""
ESA-27 Part A trial runner — generate 40 questions (20 GLM-5.2 + 20 Haiku 4.5)
and run the 4-gate quality stack on every one.

Output:
    shared/enriched-output/generation-trial/
        prompts/prompts.json
        glm-5.2/{questions.jsonl, gate-results.jsonl}
        haiku-4.5/{questions.jsonl, gate-results.jsonl}
        cost-log.json

Usage:
    python3 scripts/trial_run.py [--max-per-model N]

Environment:
    Same as generator.py (ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, etc.)

Reference: ESA-27 §"Output structure" + §"4 Gates to run on every question".
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# Make sibling scripts importable.
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import generator  # noqa: E402
from quality import run_all  # noqa: E402

logger = logging.getLogger(__name__)

OUT_ROOT = Path(__file__).resolve().parent.parent / "enriched-output" / "generation-trial"

# 4 questions per module × 5 modules = 20 prompts.
# Per-module difficulty mix: 2 easy + 1 medium + 1 hard (Phase 2 trial goal).
PROMPT_SPEC: list[tuple[str, str]] = [
    # MATHS1 — diverse: Number, Ratio, Geometry, Algebra
    ("MATHS1.M2", "Easy"),
    ("MATHS1.M3", "Easy"),
    ("MATHS1.M5", "Medium"),
    ("MATHS1.M4", "Hard"),
    # MATHS2 — Algebra, Sequences, Coord geo, Differentiation
    ("MATHS2.MM1", "Easy"),
    ("MATHS2.MM2", "Easy"),
    ("MATHS2.MM3", "Medium"),
    ("MATHS2.MM6", "Hard"),
    # PHYS — Electricity, Mechanics, Waves, Radioactivity
    ("PHYS.P1", "Easy"),
    ("PHYS.P3", "Easy"),
    ("PHYS.P6", "Medium"),
    ("PHYS.P7", "Hard"),
    # CHEM — Atomic structure, Periodic Table, Quantitative, Energetics
    ("CHEM.C1", "Easy"),
    ("CHEM.C2", "Easy"),
    ("CHEM.C4", "Medium"),
    ("CHEM.C11", "Hard"),
    # BIO — Cells, Membranes, Enzymes, Animal physiology
    ("BIO.B1", "Easy"),
    ("BIO.B2", "Easy"),
    ("BIO.B8", "Medium"),
    ("BIO.B9", "Hard"),
]

# Two A/B batches: identical prompts, different model ids.
# z.ai proxy maps the Haiku name to its internal substitute (glm-4.7 today).
BATCHES = [
    ("glm-5.2", "glm-5.2"),
    ("haiku-4.5", "claude-haiku-4-5-20251001"),
]


def build_prompts() -> list[dict[str, Any]]:
    """Render + cache the 20 deterministic prompts."""
    out = []
    for idx, (spec_code, difficulty) in enumerate(PROMPT_SPEC):
        bundle = generator.load_pattern_bundle(spec_code)
        # Deterministic seed per prompt: stable across runs/models.
        seed = int.from_bytes(
            (spec_code + difficulty).encode(), "little"
        ) & 0xFFFFFFFF
        user_prompt = generator.render_user_prompt(bundle, difficulty, seed=seed)
        out.append({
            "index": idx,
            "spec_code": spec_code,
            "difficulty": difficulty,
            "seed": seed,
            "system_prompt": generator.SYSTEM_PROMPT,
            "user_prompt": user_prompt,
            "prompt_hash": generator.hashlib.sha256(
                (generator.SYSTEM_PROMPT + "\n\n" + user_prompt).encode()
            ).hexdigest(),
        })
    return out


def run_batch(
    batch_name: str,
    model_id: str,
    prompts: list[dict[str, Any]],
    *,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Generate questions for one batch + run all gates.

    Returns (questions, gate_results, cost_summary).
    """
    out_dir = OUT_ROOT / batch_name
    out_dir.mkdir(parents=True, exist_ok=True)
    q_path = out_dir / "questions.jsonl"
    g_path = out_dir / "gate-results.jsonl"

    items = prompts if limit is None else prompts[:limit]
    total_input = total_output = 0
    total_cost = 0.0
    questions: list[dict[str, Any]] = []
    gate_results: list[dict[str, Any]] = []

    # Resume support: skip prompts whose question is already on disk.
    done_indices: set[int] = set()
    if q_path.exists():
        with q_path.open() as f:
            for line in f:
                try:
                    q = json.loads(line)
                    done_indices.add(q["trial_index"])
                    questions.append(q)
                except (json.JSONDecodeError, KeyError):
                    pass
    if g_path.exists():
        with g_path.open() as f:
            for line in f:
                try:
                    gate_results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    logger.info("Batch %s: %d already done, %d to go",
                batch_name, len(done_indices), len(items) - len(done_indices))

    q_fp = q_path.open("a")
    g_fp = g_path.open("a")

    try:
        for p in items:
            if p["index"] in done_indices:
                continue
            t0 = time.time()
            try:
                # Use generator.generate() but with our pre-rendered prompt.
                # We bypass generate()'s own prompt rendering by calling the
                # lower-level helpers, matching the A/B constraint exactly.
                bundle = generator.load_pattern_bundle(p["spec_code"])
                gen = generator.call_llm(
                    system_prompt=p["system_prompt"],
                    user_prompt=p["user_prompt"],
                    model=model_id,
                )
                parsed = generator.parse_question(gen.text)
                parsed["module"] = generator.spec_to_module(p["spec_code"])
                parsed["spec_topic"] = p["spec_code"]
                parsed["source"] = "generated"
                parsed["generated_from_template_id"] = bundle.template_id
                parsed["difficulty"] = parsed.get("difficulty_band") or p["difficulty"]
                parsed["model"] = gen.model
                parsed["prompt_hash"] = p["prompt_hash"]
                parsed["trial_index"] = p["index"]
                parsed["trial_batch"] = batch_name
                parsed["target_difficulty"] = p["difficulty"]
                parsed["elapsed_s"] = round(time.time() - t0, 2)

                total_input += gen.input_tokens
                total_output += gen.output_tokens
                total_cost += gen.cost_usd

                q_fp.write(json.dumps(parsed) + "\n")
                q_fp.flush()
                questions.append(parsed)
                logger.info(
                    "[%s] %2d/%d %s %s OK (%s, %d in/%d out, %.2fs)",
                    batch_name, p["index"] + 1, len(items),
                    p["spec_code"], p["difficulty"], gen.model,
                    gen.input_tokens, gen.output_tokens, parsed["elapsed_s"],
                )
            except Exception as exc:
                logger.error(
                    "[%s] %2d/%d %s %s FAILED: %s",
                    batch_name, p["index"] + 1, len(items),
                    p["spec_code"], p["difficulty"], exc,
                )
                traceback.print_exc()
                continue
            # Small pacing delay to avoid bursting the proxy.
            time.sleep(0.5)
    finally:
        q_fp.close()

    # Now run gates on each question in this batch.
    logger.info("Batch %s: running gates on %d questions", batch_name, len(questions))
    # Truncate gate-results file if we're rewriting from scratch.
    rerun = False
    if rerun:
        g_fp = g_path.open("w")
    else:
        g_fp = g_path.open("a")
    try:
        done_qids = {g["trial_index"] for g in gate_results if "trial_index" in g}
        for q in questions:
            if q["trial_index"] in done_qids:
                continue
            try:
                summary = run_all.run_all(q)
            except Exception as exc:
                summary = {
                    "pass": False,
                    "total_cost_usd": 0.0,
                    "within_budget": False,
                    "error": f"run_all crashed: {exc}",
                    "gates": {},
                }
                logger.error("Gate crashed for %s: %s", q.get("id"), exc)
            rec = {
                "trial_index": q["trial_index"],
                "trial_batch": batch_name,
                "spec_topic": q["spec_topic"],
                "target_difficulty": q["target_difficulty"],
                "model": q["model"],
                **summary,
            }
            g_fp.write(json.dumps(rec) + "\n")
            g_fp.flush()
            gate_results.append(rec)
            verdict = "PASS" if summary.get("pass") else "FAIL"
            logger.info(
                "[%s gate] %2d %s %s (%s, $%.5f)",
                batch_name, q["trial_index"], q["spec_topic"],
                verdict, q["model"], summary.get("total_cost_usd", 0),
            )
    finally:
        g_fp.close()

    cost_summary = {
        "model_id": model_id,
        "count": len(questions),
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cost_usd": round(total_cost, 6),
    }
    return questions, gate_results, cost_summary


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESA-27 Part A trial runner")
    p.add_argument("--max-per-model", type=int, default=None,
                   help="Limit prompts per model (for testing)")
    p.add_argument("--only", choices=["glm-5.2", "haiku-4.5"], default=None,
                   help="Run only one batch")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    prompts = build_prompts()
    prompts_path = OUT_ROOT / "prompts" / "prompts.json"
    prompts_path.parent.mkdir(parents=True, exist_ok=True)
    prompts_path.write_text(json.dumps(prompts, indent=2))
    logger.info("Wrote %d prompts to %s", len(prompts), prompts_path)

    batches = [b for b in BATCHES if args.only is None or b[0] == args.only]
    all_costs: dict[str, dict[str, Any]] = {}
    for batch_name, model_id in batches:
        logger.info("=== Batch %s (model=%s) ===", batch_name, model_id)
        _, _, cost = run_batch(
            batch_name, model_id, prompts, limit=args.max_per_model
        )
        all_costs[batch_name] = cost

    cost_log = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "batches": all_costs,
        "total_cost_usd": round(
            sum(b["cost_usd"] for b in all_costs.values()), 6
        ),
        "pricing_note": (
            "GLM-5.2 and GLM-4.5-air/GLM-4.7 (z.ai Haiku substitute) are "
            "free-tier — $0. Real Haiku 4.5 pricing only applies when "
            "ANTHROPIC_BASE_URL points at api.anthropic.com."
        ),
    }
    (OUT_ROOT / "cost-log.json").write_text(json.dumps(cost_log, indent=2))
    logger.info("Cost log: %s", cost_log)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
