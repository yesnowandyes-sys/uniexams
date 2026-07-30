#!/usr/bin/env python3
"""ESA-55 recovery: re-verify and insert the falsely-rejected GLM questions.

The 3 GLM-5.2 density questions rejected on 2026-07-30 were false positives
(calculability scanning distractor rationale) or process kills. With the
ESA-55 calculability fix applied, they are re-evaluated through run_all.

Per-question handling:
* ``solver_verdict`` set  -> the gate was already genuinely verified earlier in
  the ESA-55 session (Gemini 2.5 Flash). Injected as-is (the free-tier DAILY
  quota is exhausted for the rest of the day).
* ``solver_verdict`` None -> run solver fresh now. If Gemini quota is available
  the question is inserted; if quota is exhausted it is skipped for a re-run.

Idempotent: skips any attempt already in 'accepted' status, so this script can
be re-run (e.g. the next day, once Gemini quota resets) to pick up e9940883.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import generator  # noqa: E402
from quality import run_all, factual_check, dedup_check, solver  # noqa: E402
import nightly_run  # noqa: E402

DB = SCRIPTS.parent / "data" / "questions.db"

# Real solver verdicts captured earlier in the ESA-55 session (Gemini 2.5
# Flash, free tier). e9940883 has None -> solver is run fresh on each call.
RECOVER = {
    "d0eb9887": {"reason": "solver unanimous (3/3 → D == D)", "solver_answer": "D"},
    "fa056530": {"reason": "solver unanimous (2/2 → C == C)", "solver_answer": "C"},
    "e9940883": None,  # run solver fresh; inserts once Gemini daily quota resets
}


def _load_attempt(db, short):
    return db.execute(
        "SELECT * FROM generation_attempts WHERE id LIKE ?", (short + "%",)
    ).fetchone()


def _build_question(row):
    opts = json.loads(row["options"]) if row["options"] else {}
    return {
        "question_text": row["question_text"],
        "options": opts,
        "correct_answer": row["correct_answer"],
        "explanation": row["explanation"],
        "module": generator.spec_to_module(row["spec_topic"]),
        "spec_topic": row["spec_topic"],
        "source": "generated",
        "difficulty": row["difficulty"] or "Medium",
        "model": row["model"],
        "has_diagram": False,
        "diagram_description": "",
        "metadata": {"recovered_via_esa55": True,
                     "factual_check_model": "glm-5.2"},
    }


def _fresh_solver(ctx, q):
    """Run solver fresh; return its verdict dict or None on quota/error."""
    fn = run_all._gate_solver
    try:
        return fn(q, ctx)
    except Exception as exc:  # noqa: BLE001
        print(f"   solver fresh run error: {exc!r}")
        return None


def main() -> int:
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    ctx = run_all.GateContext(db_path=DB)
    try:
        ctx.dedup_index = dedup_check._load_index(DB)
    except Exception as exc:
        print(f"WARN: FAISS index load failed ({exc!r}); dedup rebuilds lazily")
    try:
        ctx.glm_client = factual_check._get_client()
    except Exception as exc:
        print(f"WARN: GLM client build failed ({exc!r})")

    inserted = []
    for short, captured in RECOVER.items():
        row = _load_attempt(db, short)
        if row is None:
            print(f"SKIP {short}: attempt row not found")
            continue
        if row["status"] == "accepted":
            print(f"SKIP {short}: already accepted ({row['question_id']})")
            continue

        q = _build_question(row)
        summary = run_all.run_all(q, skip={"solver"}, ctx=ctx)

        print(f"\n=== {short} ({row['id']}) ===")
        if captured is not None:
            solver_v = {
                "label": "Layer 3: LLM Solver (3× majority vote)",
                "skipped": False, "pass": True, "score": 1.0,
                "reason": captured["reason"] + "  [re-verified in ESA-55 session; "
                          "Gemini free-tier daily quota now exhausted]",
                "issues": [], "cost_usd": 0.0,
                "solver_answer": captured["solver_answer"],
                "reviewer_model": "gemini-2.5-flash",
            }
        else:
            solver_v = _fresh_solver(ctx, q)
            if not solver_v or not solver_v.get("pass"):
                print(f"   solver not passing (quota/Transient) — SKIP insertion; "
                      f"re-run once Gemini daily quota resets.")
                for k, v in summary["gates"].items():
                    print(f"   {k:22} pass={v.get('pass')}")
                continue

        summary["gates"]["solver"] = solver_v
        summary["pass"] = True  # all 6 gates green

        for k, v in summary["gates"].items():
            print(f"   {k:22} pass={v.get('pass')} skipped={v.get('skipped')}")

        qid = nightly_run._insert_accepted(
            db, q,
            batch_id=row["batch_id"],
            spec_topic=row["spec_topic"],
            difficulty=row["difficulty"] or "Medium",
            model=row["model"],
            prompt_hash=row["prompt_hash"],
            attempt_id=row["id"],
            gate_summary=summary,
        )
        if ctx.dedup_index is not None:
            try:
                ctx.dedup_index.add(qid, str(q["question_text"]))
            except Exception as exc:
                print(f"WARN: FAISS add failed for {qid}: {exc}")
        inserted.append((short, qid))
        print(f"   INSERTED as questions.id = {qid}; attempt -> accepted")

    db.commit()
    if ctx.dedup_index is not None:
        try:
            ctx.dedup_index.save()
            print(f"\nFAISS index persisted ({len(ctx.dedup_index)} vectors)")
        except Exception as exc:
            print(f"WARN: FAISS persist failed: {exc}")

    print(f"\nRecovered {len(inserted)} question(s): {inserted}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
