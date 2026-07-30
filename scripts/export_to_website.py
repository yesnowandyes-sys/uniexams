#!/usr/bin/env python3
"""
Export accepted generated questions to the website query path — ESA-24 §3.

Reads every generation_attempts row with status='accepted' (joined to
questions for the full row), shapes each to the website's ESAT JSON
schema, and writes a single JSONL file at
`shared/enriched-output/website/generated.jsonl` plus a pretty-printed
manifest with count + sha256.

Idempotent: a full rewrite every run. Designed to run after the nightly
batch lands so the website picks up new questions on next deploy.

Usage:
    python3 export_to_website.py
    python3 export_to_website.py --out /custom/path.jsonl
    python3 export_to_website.py --since-batch nightly-20260715T...

Reference: ESA-24 task §3 (export_to_website.py).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SHARED_DIR = Path(__file__).resolve().parent.parent
DB_PATH = SHARED_DIR / "data" / "questions.db"
DEFAULT_OUT = SHARED_DIR / "enriched-output" / "website" / "generated.jsonl"


def _load_accepted(db: sqlite3.Connection, since_batch: str | None) -> list[dict[str, Any]]:
    """Return shaped question dicts for all accepted attempts."""
    sql = """
        SELECT q.id, q.module, q.question_text, q.options, q.correct_answer,
               q.explanation, q.metadata, q.generated_from_template_id,
               q.difficulty_score, ga.spec_topic, ga.difficulty, ga.model,
               ga.batch_id, ga.prompt_hash, ga.created_at
        FROM generation_attempts ga
        JOIN questions q ON q.id = ga.question_id
        WHERE ga.status = 'accepted'
    """
    params: tuple[Any, ...] = ()
    if since_batch:
        sql += " AND ga.batch_id >= ?"
        params = (since_batch,)
    sql += " ORDER BY ga.created_at ASC"
    cur = db.execute(sql, params)
    rows = cur.fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        (qid, module, qtext, options_json, correct, explanation,
         metadata_json, template_id, diff_score, spec_topic, difficulty,
         model, batch_id, prompt_hash, created_at) = r
        try:
            options = json.loads(options_json) if options_json else {}
        except json.JSONDecodeError:
            options = {}
        try:
            metadata = json.loads(metadata_json) if metadata_json else {}
        except json.JSONDecodeError:
            metadata = {}
        out.append({
            "id": qid,
            "source": "generated",
            "exam_type": "ESAT",
            "module": module,
            "spec_topic": spec_topic,
            "difficulty": difficulty or metadata.get("difficulty_band", ""),
            "question_text": qtext,
            "options": options,
            "correct_answer": correct,
            "explanation": explanation,
            "model": model,
            "batch_id": batch_id,
            "prompt_hash": prompt_hash,
            "generated_from_template_id": template_id,
            "difficulty_score": diff_score,
            "created_at": created_at,
        })
    return out


def export(
    *,
    out_path: Path = DEFAULT_OUT,
    since_batch: str | None = None,
) -> dict[str, Any]:
    """Write accepted generated questions to JSONL. Returns manifest dict."""
    db = sqlite3.connect(DB_PATH)
    try:
        questions = _load_accepted(db, since_batch)
    finally:
        db.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    # sha256 over the file body for downstream deploy verification.
    body_hash = hashlib.sha256(out_path.read_bytes()).hexdigest()
    manifest = {
        "path": str(out_path),
        "count": len(questions),
        "sha256": body_hash,
        "since_batch": since_batch,
        "exported_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ",
                                                   __import__("time").gmtime()),
    }
    manifest_path = out_path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Exported %d questions to %s (sha256=%s)",
                len(questions), out_path, body_hash[:12])
    return manifest


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export generated questions to website")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT,
                   help=f"Output JSONL path (default {DEFAULT_OUT})")
    p.add_argument("--since-batch", default=None,
                   help="Only export rows with batch_id >= this prefix")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    manifest = export(out_path=args.out, since_batch=args.since_batch)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
