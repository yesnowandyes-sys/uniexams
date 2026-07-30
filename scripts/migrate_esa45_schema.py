#!/usr/bin/env python3
"""
ESA-45 schema migration — add columns the rebuilt verification stack needs.

Two columns were missing from the live `data/questions.db`:

1. `generation_attempts.difficulty` (TEXT) — `nightly_run._attempt_one`
   INSERTs the target difficulty band here. Without it the INSERT raises
   "table generation_attempts has no column named difficulty" and the whole
   nightly run crashes (this was the live blocker recorded in memory).

2. `questions.difficulty_score_structural` (REAL) — Layer 4
   (`structural_difficulty.py`) produces a deterministic 1-10 structural
   difficulty to sit alongside the LLM self-assessment `difficulty_score`.
   Both are stored so we can later compare which predicts exam performance.

Idempotent: inspects PRAGMA table_info and only adds a column when absent, so
it is safe to re-run on any DB state (corpus-only, post-cold-store, etc.).

Usage:
    python3 migrate_esa45_schema.py [--db data/questions.db]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "questions.db"

# (table, column, DDL type clause, rationale)
MIGRATIONS = [
    (
        "generation_attempts",
        "difficulty",
        "TEXT",
        "target difficulty band for the attempt (Easy/Medium/Hard/Very Hard)",
    ),
    (
        "questions",
        "difficulty_score_structural",
        "REAL",
        "Layer 4 deterministic structural difficulty score (1-10)",
    ),
]


def _has_column(db: sqlite3.Connection, table: str, column: str) -> bool:
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    # row schema: (cid, name, type, notnull, dflt_value, pk)
    return any(r[1] == column for r in rows)


def migrate(db_path: Path) -> list[str]:
    """Apply all pending ESA-45 migrations. Returns the list of columns added."""
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    db = sqlite3.connect(db_path)
    applied: list[str] = []
    try:
        for table, column, ddl_type, why in MIGRATIONS:
            if _has_column(db, table, column):
                continue
            db.execute(f'ALTER TABLE {table} ADD COLUMN "{column}" {ddl_type}')
            db.commit()
            applied.append(f"{table}.{column}")
            print(f"  + added {table}.{column} ({ddl_type}) — {why}")
        if not applied:
            print("  (all ESA-45 columns already present — nothing to do)")
    finally:
        db.close()
    return applied


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESA-45 schema migration")
    p.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to questions.db")
    args = p.parse_args(argv)

    print(f"Migrating {args.db} ...")
    applied = migrate(args.db)
    print(f"Done. {len(applied)} column(s) added: {applied or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
