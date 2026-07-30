#!/usr/bin/env python3
"""
Nightly generation orchestrator — ESA-24 / ESA-17 §13.2 + §13.3 + §14.4.

Pulls the most under-represented (module, topic, difficulty) tuple from
coverage_tracker, calls the generator backend, runs all 6 quality gates,
stores accepted questions into `questions` + `generation_attempts` +
`quality_reviews`, logs rejected attempts, and writes a per-run summary.

Loops until `--batch-size` accepted questions are landed OR the coverage
pool is exhausted OR a hard cost ceiling is hit. Each question gets up
to 3 generation attempts (orchestration-review §14.4); on each attempt
we re-pick the next under-represented tuple so retries don't burn a
single stuck cell.

Backend dispatch (ESA-53): `--model glm-*` routes to the z.ai GLM
generator (scripts/generator_glm.py); any other model uses the Gemini
generator (scripts/generator.py). For GLM, a weekly quota guard runs
first — if weekly.percentage > weekly.elapsedPct, GLM calls are skipped
unless --ignore-quota is set.

Usage:
    python3 nightly_run.py                    # default batch (50), Gemini
    python3 nightly_run.py --batch-size 5     # smoke test
    python3 nightly_run.py --model glm-5.2 --batch-size 100
    python3 nightly_run.py --model glm-5.2 --batch-size 1 --ignore-quota
    python3 nightly_run.py --dry-run          # plan only, no LLM calls

Reference: ESA-24 task §2 + §Acceptance, strategy §13.2/§13.3,
orchestration-review §14.4 (max retries).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import secrets
import sqlite3
import sys
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import generator  # noqa: E402
from quality import run_all  # noqa: E402
import coverage_tracker  # noqa: E402

logger = logging.getLogger(__name__)

SHARED_DIR = SCRIPTS_DIR.parent
DB_PATH = SHARED_DIR / "data" / "questions.db"
LOGS_DIR = SHARED_DIR / "logs" / "nightly"
COST_LOG_PATH = SHARED_DIR / "logs" / "nightly_cost.jsonl"

MAX_ATTEMPTS_PER_QUESTION = 3  # orchestration-review §14.4
DEFAULT_BATCH_SIZE = 50
DEFAULT_MODEL = generator.PRIMARY_MODEL
HARD_COST_CEILING_USD = 5.0  # never exceed this in one run


def _is_glm_model(model: str) -> bool:
    """True for z.ai GLM models (``glm-*``)."""
    return bool(model) and model.lower().startswith("glm")


def _resolve_backend(model: str):
    """Return the generator module for the requested model.

    ESA-53 / ESA-52: nightly_run previously hard-coded ``import generator``
    (Gemini-only), so ``--model glm-5.2`` was passed verbatim into Google's
    Gemini SDK and failed every attempt — it never reached z.ai. GLM models
    now route to ``scripts/generator_glm.py``; everything else stays on
    Gemini. ``generator_glm`` is imported lazily because it pulls in the
    heavier ``openai`` SDK, which Gemini-only runs should not pay for.
    """
    if _is_glm_model(model):
        import generator_glm  # noqa: WPS433 — lazy import, see docstring
        return generator_glm
    return generator


def _build_glm_client():
    """Build the z.ai OpenAI client for the GLM backend.

    Mirrors ``scripts/generate_and_verify_glm.py``. Raises ``RuntimeError``
    with a clear message if no API key is resolvable, so the caller surfaces
    one clean error instead of churning failed attempts.
    """
    import generator_glm
    import openai

    api_key = generator_glm.resolve_api_key(None)
    if not api_key:
        raise RuntimeError(
            "No z.ai API key resolvable (set ZAI_API_KEY or configure the "
            "OpenClaw z.ai catalog) — cannot use the GLM backend."
        )
    return openai.OpenAI(api_key=api_key, base_url=generator_glm.ZAI_BASE_URL)


def _glm_quota_allows() -> tuple[bool, str]:
    """Weekly pacing guard for the GLM backend (ESA-52 quota guard).

    The task spec: if ``weekly.percentage > weekly.elapsedPct`` (i.e.
    negative weekly headroom), skip GLM-5.2 calls. Mirrors the weekly
    half of ``generate_and_verify_glm._check_quota_allows``. Fails open
    (returns allowed) if the local quota endpoint is unreachable.
    """
    try:
        import generator_glm
        headroom = generator_glm._quota_headroom_pct()
        if headroom is None:
            return True, "quota endpoint unreachable — failing open"
        threshold = generator_glm.QUOTA_HEADROOM_THRESHOLD_PCT
        if headroom <= threshold:
            return False, (
                f"weekly headroom {headroom:.1f}% <= threshold {threshold}% "
                f"(weekly.percentage > weekly.elapsedPct) — pacing guard fires"
            )
        return True, f"weekly headroom {headroom:.1f}%"
    except Exception as exc:  # never let the guard itself crash the run
        return True, f"quota check error ({exc!r}) — failing open"


@dataclass
class RunSummary:
    """Per-run bookkeeping written to logs/nightly/<batch_id>.json."""

    batch_id: str
    started_at: str
    ended_at: str = ""
    model: str = ""
    dry_run: bool = False
    target_batch_size: int = 0
    accepted: int = 0
    rejected: int = 0
    total_attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cells_targeted: list[dict[str, Any]] = field(default_factory=list)
    reject_reasons: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "model": self.model,
            "dry_run": self.dry_run,
            "target_batch_size": self.target_batch_size,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "total_attempts": self.total_attempts,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "cells_targeted": self.cells_targeted,
            "reject_reasons": self.reject_reasons,
            "errors": self.errors,
        }


def _insert_accepted(
    db: sqlite3.Connection,
    question: dict[str, Any],
    *,
    batch_id: str,
    spec_topic: str,
    difficulty: str,
    model: str,
    prompt_hash: str,
    attempt_id: str,
    gate_summary: dict[str, Any],
) -> str:
    """Insert accepted question into `questions` + finalize attempt row.

    Returns the new questions.id.
    """
    qid = question.get("id") or f"gen-{uuid.uuid4()}"
    options = question.get("options", {})
    if isinstance(options, dict):
        options_json = json.dumps(options)
    else:
        options_json = json.dumps(options) if options else "{}"
    metadata = question.get("metadata") or {}
    if isinstance(metadata, dict):
        metadata["generated"] = True
        metadata["spec_topic"] = spec_topic
        metadata["difficulty_band"] = difficulty
        metadata["batch_id"] = batch_id
        metadata["model"] = model
        # ESA-43: store diagram fields in metadata
        metadata["has_diagram"] = question.get("has_diagram", False)
        metadata["diagram_description"] = question.get("diagram_description", "")
        metadata_json = json.dumps(metadata)
    else:
        metadata_json = json.dumps({"generated": True})

    # ESA-45 Layer 4: deterministic structural difficulty (sits alongside the
    # LLM self-assessment difficulty_score).
    structural_score = (gate_summary or {}).get("difficulty_score_structural")

    db.execute(
        """INSERT INTO questions
           (id, exam_type, module, question_number, question_text, options,
            correct_answer, explanation, metadata, source,
            generated_from_template_id, difficulty_score,
            difficulty_score_structural, subject)
           VALUES (?, 'ESAT', ?, 0, ?, ?, ?, ?, ?, 'generated', ?, ?, ?, ?)""",
        (
            qid,
            question.get("module", ""),
            question.get("question_text", ""),
            options_json,
            str(question.get("correct_answer", "")),
            question.get("explanation", ""),
            metadata_json,
            question.get("generated_from_template_id"),
            question.get("difficulty_score"),
            structural_score,
            question.get("subject", ""),
        ),
    )
    # Finalize the attempt row + write per-gate reviews.
    db.execute(
        """UPDATE generation_attempts
           SET status='accepted', question_id=?, reject_reason=NULL
           WHERE id=?""",
        (qid, attempt_id),
    )
    _write_gate_reviews(db, attempt_id=attempt_id, gate_summary=gate_summary,
                        model=model)
    return qid


def _write_gate_reviews(
    db: sqlite3.Connection,
    *,
    attempt_id: str,
    gate_summary: dict[str, Any],
    model: str,
) -> None:
    """Persist per-gate verdicts into quality_reviews."""
    gates = gate_summary.get("gates", {}) or {}
    for key, payload in gates.items():
        if not isinstance(payload, dict):
            continue
        if payload.get("skipped"):
            continue
        db.execute(
            """INSERT INTO quality_reviews
               (id, attempt_id, gate, passed, score, reason, reviewer_model, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                attempt_id,
                key,
                1 if payload.get("pass") else 0,
                payload.get("score"),
                (payload.get("reason") or "")[:500],
                payload.get("reviewer_model") or model,
                json.dumps({"label": payload.get("label", ""),
                            "cost_usd": payload.get("cost_usd", 0.0)}),
            ),
        )


def _reject_attempt(
    db: sqlite3.Connection,
    *,
    attempt_id: str,
    reason: str,
    gate_summary: dict[str, Any] | None,
    model: str,
) -> None:
    """Mark attempt rejected + persist per-gate reviews for forensics."""
    db.execute(
        "UPDATE generation_attempts SET status='rejected', reject_reason=? WHERE id=?",
        (reason[:200], attempt_id),
    )
    if gate_summary:
        _write_gate_reviews(db, attempt_id=attempt_id,
                            gate_summary=gate_summary, model=model)


def _first_failing_gate(gate_summary: dict[str, Any]) -> tuple[str, str]:
    """Return (gate_key, short_reason) for the first failing non-skipped gate."""
    for key, payload in (gate_summary.get("gates") or {}).items():
        if not isinstance(payload, dict):
            continue
        if payload.get("skipped"):
            continue
        if not payload.get("pass"):
            reason = (payload.get("reason") or "")[:120]
            return key, reason or f"{key}_failed"
    return "unknown", "no_failing_gate"


def _pick_next_tuple(
    db: sqlite3.Connection,
    *,
    skip: set[tuple[str, str]] | None = None,
    rotation_offset: int = 0,
) -> dict[str, Any] | None:
    """Pull the most under-represented (module, topic, difficulty).

    `skip` drops specific (topic, difficulty) tuples from consideration —
    used to avoid re-trying tuples that already exhausted retries this batch.
    `rotation_offset` breaks ties round-robin: when N tuples are tied at
    the same fill_ratio, we pick offset % N rather than always the
    alphabetical-first one.
    """
    targets = coverage_tracker.load_targets()
    if not targets:
        return None
    generated_counts = coverage_tracker._count_generated(db)
    coverage = coverage_tracker.compute_coverage(targets, generated_counts=generated_counts)
    candidates = [c for c in coverage if c.target_count > 0]
    if skip:
        candidates = [c for c in candidates
                      if (c.topic, c.difficulty) not in skip]
    if not candidates:
        return None
    candidates.sort(key=lambda c: (
        c.fill_ratio,            # least-filled first
        -c.shortfall,            # then by largest shortfall desc
        c.module, c.topic, c.difficulty,
    ))
    # Among the tied leading cells (same fill_ratio AND same shortfall),
    # rotate by offset so we don't hammer the alphabetically-first cell.
    if rotation_offset > 0:
        lead_ratio = candidates[0].fill_ratio
        lead_shortfall = candidates[0].shortfall
        tied = [c for c in candidates
                if c.fill_ratio == lead_ratio and c.shortfall == lead_shortfall]
        if len(tied) > 1:
            idx = rotation_offset % len(tied)
            p = tied[idx]
        else:
            p = candidates[0]
    else:
        p = candidates[0]
    return {
        "module": p.module,
        "topic": p.topic,
        "difficulty": p.difficulty,
        "fill_ratio": p.fill_ratio,
        "shortfall": p.shortfall,
        "current_count": p.current_count,
        "target_count": p.target_count,
    }


def _attempt_one(
    db: sqlite3.Connection,
    *,
    batch_id: str,
    target: dict[str, Any],
    model: str,
    seed: int,
    dry_run: bool = False,
    ctx: Any = None,
    backend=generator,
    glm_client: Any = None,
) -> tuple[bool, dict[str, Any], str]:
    """Generate + gate one question for the target tuple.

    Returns (accepted, attempt_record, reject_reason).
    `attempt_record` has: input_tokens, output_tokens, cost_usd,
    model, spec_topic, difficulty, question_text, options,
    correct_answer, explanation, prompt_hash.
    """
    spec_topic = target["topic"]
    difficulty = target["difficulty"]

    attempt_id = str(uuid.uuid4())
    prompt_hash_pre = "dry-run" if dry_run else ""

    if dry_run:
        # Plan-only: don't call the LLM. Return a synthetic record.
        rec = {
            "attempt_id": attempt_id,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "model": model,
            "spec_topic": spec_topic,
            "difficulty": difficulty,
            "question_text": "",
            "options": {},
            "correct_answer": "",
            "explanation": "",
            "prompt_hash": prompt_hash_pre,
        }
        return True, rec, ""

    # Real generation path. GLM models route to generator_glm, which takes a
    # pre-built z.ai OpenAI client as its first positional arg (ESA-53).
    if _is_glm_model(model):
        question, gen = backend.generate(
            glm_client, spec_topic, difficulty,
            model=model, seed=seed,
        )
    else:
        question, gen = backend.generate(
            spec_code=spec_topic,
            difficulty=difficulty,
            model=model,
            seed=seed,
        )
    question["module"] = backend.spec_to_module(spec_topic)
    question["spec_topic"] = spec_topic
    question["source"] = "generated"
    question["difficulty"] = question.get("difficulty_band") or difficulty
    question["model"] = gen.model

    # Pre-insert the attempt as pending so we can always trace it.
    options_json = json.dumps(question.get("options") or {})
    prompt_hash = hashlib.sha256(
        (backend.SYSTEM_PROMPT + "\n\n" + spec_topic + difficulty + str(seed)).encode()
    ).hexdigest()
    db.execute(
        """INSERT INTO generation_attempts
           (id, batch_id, spec_topic, difficulty, model, prompt_hash,
            question_text, options, correct_answer, explanation, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (
            attempt_id, batch_id, spec_topic, difficulty, gen.model, prompt_hash,
            question.get("question_text", ""),
            options_json,
            str(question.get("correct_answer", "")),
            question.get("explanation", ""),
        ),
    )
    db.commit()

    rec = {
        "attempt_id": attempt_id,
        "input_tokens": gen.input_tokens,
        "output_tokens": gen.output_tokens,
        "cost_usd": gen.cost_usd,
        "model": gen.model,
        "spec_topic": spec_topic,
        "difficulty": difficulty,
        "prompt_hash": prompt_hash,
    }

    # Run the rebuilt ESA-45 verification stack (Layers 1-5 + 7).
    try:
        gate_summary = run_all.run_all(question, ctx=ctx)
    except Exception as exc:
        logger.exception("run_all crashed for %s", spec_topic)
        _reject_attempt(db, attempt_id=attempt_id, reason=f"gate_crash:{exc}",
                        gate_summary=None, model=gen.model)
        return False, rec, f"gate_crash:{exc}"

    if not gate_summary.get("pass"):
        gate_key, reason = _first_failing_gate(gate_summary)
        _reject_attempt(db, attempt_id=attempt_id, reason=f"{gate_key}:{reason}",
                        gate_summary=gate_summary, model=gen.model)
        return False, {**rec,
                       "question": question,
                       "gate_summary": gate_summary}, f"{gate_key}:{reason}"

    # Budget guard: reject if over per-question budget.
    if not gate_summary.get("within_budget"):
        _reject_attempt(db, attempt_id=attempt_id, reason="cost_over_budget",
                        gate_summary=gate_summary, model=gen.model)
        return False, {**rec, "question": question,
                       "gate_summary": gate_summary}, "cost_over_budget"

    # Accept: insert into questions, finalize attempt, write reviews.
    qid = _insert_accepted(
        db, question,
        batch_id=batch_id,
        spec_topic=spec_topic,
        difficulty=difficulty,
        model=gen.model,
        prompt_hash=prompt_hash,
        attempt_id=attempt_id,
        gate_summary=gate_summary,
    )
    db.commit()

    # ESA-45 Layer 5: add the accepted question to the FAISS index so later
    # attempts in this batch (and future runs) dedup against it.
    if ctx is not None and getattr(ctx, "dedup_index", None) is not None:
        try:
            ctx.dedup_index.add(qid, str(question.get("question_text", "")))
        except Exception as exc:
            logger.warning("FAISS index update failed for %s: %s", qid, exc)

    return True, {**rec, "question_id": qid, "question": question}, ""


def _build_gate_context() -> Any:
    """Build the shared GateContext for the batch (FAISS index + GLM client).

    Loading the FAISS index (~8 s) and the GLM client once per batch — instead
    of per question — is a large speed-up. Every resource is optional: if one
    fails to load the owning gate falls back to lazy-loading or skips.
    """
    from quality import dedup_check, factual_check  # local: avoid import cost

    ctx = run_all.GateContext(db_path=DB_PATH)
    try:
        ctx.dedup_index = dedup_check._load_index(DB_PATH)
        logger.info("FAISS dedup index loaded (%d vectors)", len(ctx.dedup_index))
    except Exception as exc:
        logger.warning("FAISS index load failed — dedup will rebuild lazily: %s", exc)
    try:
        ctx.glm_client = factual_check._get_client()
        logger.info("GLM client ready for factual check (Layer 7)")
    except Exception as exc:
        logger.warning("GLM client unavailable — factual check will lazy-load: %s", exc)
    return ctx


def run_nightly(
    *,
    batch_size: int,
    model: str,
    dry_run: bool = False,
    max_attempts_per_question: int = MAX_ATTEMPTS_PER_QUESTION,
    ignore_quota: bool = False,
) -> RunSummary:
    """Top-level loop. Returns the RunSummary (also written to disk)."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    batch_id = f"nightly-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{secrets.token_hex(3)}"
    summary = RunSummary(
        batch_id=batch_id,
        started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        model=model,
        dry_run=dry_run,
        target_batch_size=batch_size,
    )
    logger.info("=== nightly_run batch=%s model=%s target=%d dry_run=%s ===",
                batch_id, model, batch_size, dry_run)

    backend = _resolve_backend(model)
    glm_client = None
    skip_generation = False

    # Resolve the backend and (for GLM) honour the weekly quota guard BEFORE
    # paying the ~8 s cost of loading the FAISS index / building the gate
    # context. Task quota guard: if weekly.percentage > weekly.elapsedPct,
    # skip GLM-5.2 calls.
    if dry_run:
        be = "generator_glm" if _is_glm_model(model) else "generator (Gemini)"
        logger.info("Dry-run — backend would be %s, no LLM calls.", be)
    elif _is_glm_model(model):
        allowed, info = _glm_quota_allows()
        if allowed:
            logger.info("GLM backend selected — z.ai client ready (%s).", info)
        elif ignore_quota:
            logger.warning(
                "GLM backend selected but QUOTA GUARD FIRED (%s). "
                "--ignore-quota set: proceeding anyway (smoke/manual run).",
                info,
            )
        else:
            logger.warning(
                "GLM backend selected but QUOTA GUARD FIRED (%s). "
                "Skipping GLM calls this run. Re-run when weekly pacing "
                "recovers, pass --model %s for Gemini, or --ignore-quota to force.",
                info, generator.PRIMARY_MODEL,
            )
            summary.errors.append(f"glm_quota_blocked:{info}")
            skip_generation = True
        if not skip_generation:
            try:
                glm_client = _build_glm_client()
            except Exception as exc:  # noqa: BLE001
                logger.error("Could not build GLM client: %s", exc)
                summary.errors.append(f"glm_client_build_failed:{exc}")
                skip_generation = True
    else:
        logger.info("Gemini backend selected (model=%s).", model)

    ctx = None if (dry_run or skip_generation) else _build_gate_context()

    db = sqlite3.connect(DB_PATH)
    exhausted_tuples: set[tuple[str, str]] = set()
    rotation_counter = 0
    try:
        while not skip_generation and summary.accepted < batch_size:
            if summary.cost_usd >= HARD_COST_CEILING_USD:
                logger.warning("Hit hard cost ceiling $%.2f — stopping early",
                               HARD_COST_CEILING_USD)
                summary.errors.append(
                    f"cost_ceiling_hit:{summary.cost_usd:.2f}"
                )
                break

            target = _pick_next_tuple(
                db,
                skip=exhausted_tuples,
                rotation_offset=rotation_counter,
            )
            rotation_counter += 1
            if not target:
                logger.info("Coverage pool exhausted at %d/%d accepted",
                            summary.accepted, batch_size)
                break

            accepted_this_question = False
            summary.cells_targeted.append({
                "module": target["module"],
                "topic": target["topic"],
                "difficulty": target["difficulty"],
                "fill_ratio_before": target["fill_ratio"],
            })

            for attempt_n in range(1, max_attempts_per_question + 1):
                summary.total_attempts += 1
                # Seed: stable per (tuple, attempt) so retries differ but
                # reproduce.
                seed = abs(hash((target["topic"], target["difficulty"], attempt_n))) & 0xFFFFFFFF
                try:
                    ok, rec, reason = _attempt_one(
                        db,
                        batch_id=batch_id,
                        target=target,
                        model=model,
                        seed=seed,
                        dry_run=dry_run,
                        ctx=ctx,
                        backend=backend,
                        glm_client=glm_client,
                    )
                except Exception as exc:
                    logger.exception("Attempt %d crashed for %s",
                                     attempt_n, target["topic"])
                    summary.errors.append(f"{target['topic']}:{target['difficulty']}:{exc}")
                    continue

                summary.input_tokens += rec.get("input_tokens", 0)
                summary.output_tokens += rec.get("output_tokens", 0)
                summary.cost_usd += rec.get("cost_usd", 0.0)

                if ok:
                    summary.accepted += 1
                    accepted_this_question = True
                    logger.info(
                        "[accept %d/%d] %s %s (attempt %d, %d+%d tok, $%.5f)",
                        summary.accepted, batch_size,
                        target["topic"], target["difficulty"],
                        attempt_n, rec.get("input_tokens", 0),
                        rec.get("output_tokens", 0), rec.get("cost_usd", 0.0),
                    )
                    break
                else:
                    summary.reject_reasons[reason] = (
                        summary.reject_reasons.get(reason, 0) + 1
                    )
                    logger.info(
                        "[reject attempt %d/%d] %s %s — %s",
                        attempt_n, max_attempts_per_question,
                        target["topic"], target["difficulty"], reason,
                    )

                if dry_run:
                    # In dry-run we only do one pass per tuple.
                    break

            if not accepted_this_question and not dry_run:
                summary.rejected += 1
                # Mark this tuple exhausted for the rest of the batch so
                # we don't hammer the same cell.
                exhausted_tuples.add((target["topic"], target["difficulty"]))
                logger.warning(
                    "Gave up on %s %s after %d attempts (%d tuples exhausted)",
                    target["topic"], target["difficulty"],
                    max_attempts_per_question, len(exhausted_tuples),
                )
    finally:
        db.close()

    # ESA-45 Layer 5: persist the incrementally-updated FAISS index so future
    # runs dedup against this batch's accepted questions too (corpus + all
    # previously generated). The in-memory add() during the loop only covers
    # intra-batch dedup; this writes it to data/faiss_index/.
    if ctx is not None and getattr(ctx, "dedup_index", None) is not None:
        try:
            ctx.dedup_index.save()
            logger.info("FAISS index persisted (%d vectors)", len(ctx.dedup_index))
        except Exception as exc:
            logger.warning("FAISS index persist failed: %s", exc)

    summary.ended_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    summary_path = LOGS_DIR / f"{batch_id}.json"
    summary_path.write_text(json.dumps(summary.to_dict(), indent=2))
    logger.info("Summary written to %s", summary_path)

    # Append to cost log.
    COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COST_LOG_PATH.open("a") as f:
        f.write(json.dumps({
            "batch_id": batch_id,
            "ts": summary.ended_at,
            "model": model,
            "dry_run": summary.dry_run,
            "accepted": summary.accepted,
            "rejected": summary.rejected,
            "total_attempts": summary.total_attempts,
            "input_tokens": summary.input_tokens,
            "output_tokens": summary.output_tokens,
            "cost_usd": round(summary.cost_usd, 6),
        }) + "\n")
    return summary


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT nightly orchestrator")
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                   help=f"Target accepted questions per run (default {DEFAULT_BATCH_SIZE})")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"Generator model (default {DEFAULT_MODEL})")
    p.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS_PER_QUESTION,
                   help="Max generation attempts per question before discard")
    p.add_argument("--dry-run", action="store_true",
                   help="Plan only — no LLM calls, no DB writes")
    p.add_argument("--ignore-quota", action="store_true",
                   help="Bypass the GLM weekly quota guard (smoke/manual runs only)")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    summary = run_nightly(
        batch_size=args.batch_size,
        model=args.model,
        dry_run=args.dry_run,
        max_attempts_per_question=args.max_attempts,
        ignore_quota=args.ignore_quota,
    )
    # Stdout summary line for cron logs.
    print(json.dumps({
        "batch_id": summary.batch_id,
        "accepted": summary.accepted,
        "rejected": summary.rejected,
        "total_attempts": summary.total_attempts,
        "cost_usd": round(summary.cost_usd, 6),
        "input_tokens": summary.input_tokens,
        "output_tokens": summary.output_tokens,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
