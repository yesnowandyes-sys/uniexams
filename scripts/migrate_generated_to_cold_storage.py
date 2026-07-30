#!/usr/bin/env python3
"""
ESA-44 Part A — Move generated questions into cold storage.

The main `questions` table should contain ONLY the enriched corpus questions
(1,687). All `source='generated'` questions (ids like `gen-...`) are moved to a
new archive table `questions_generated_v1` (identical schema) and deleted from
`questions`. Archived rows stay queryable for audit but are NOT served by the
website and NOT used as generation exemplars.

Design:
  * `questions_generated_v1` is created with the *exact* CREATE statement of
    `questions` (constraints + defaults preserved) — derived at runtime so it
    never drifts from the live schema.
  * Idempotent: safe to run repeatedly. Re-runs are no-ops once everything is
    archived.
  * Single transaction; the DELETE only runs if the INSERT row count matches
    the number of source rows, so a partial failure cannot lose data.

Usage:
    python3 scripts/migrate_generated_to_cold_storage.py [--db PATH] [--dry-run]

Reference: ESA-44 Part A.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "questions.db"
ARCHIVE_TABLE = "questions_generated_v1"


def get_create_sql(conn: sqlite3.Connection, table: str) -> str:
    """Return the original CREATE statement for `table`."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"No CREATE statement found for table {table!r}")
    return row[0]


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--dry-run", action="store_true", help="Report only; write nothing.")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"[err] database not found: {db}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        gen_count = conn.execute(
            "SELECT COUNT(*) FROM questions WHERE source='generated'"
        ).fetchone()[0]
        corpus_count = conn.execute(
            "SELECT COUNT(*) FROM questions WHERE source='corpus'"
        ).fetchone()[0]
        other_count = total - gen_count - corpus_count
        print(f"[info] questions total     = {total}")
        print(f"[info]   source='corpus'   = {corpus_count}")
        print(f"[info]   source='generated'= {gen_count}")
        if other_count:
            print(f"[warn]   other sources    = {other_count} (left in place)")

        if gen_count == 0 and table_exists(conn, ARCHIVE_TABLE):
            print("[info] nothing to move; archive already populated.")
            return 0

        if args.dry_run:
            print(f"[dry-run] would archive {gen_count} generated rows into "
                  f"{ARCHIVE_TABLE} and delete them from questions.")
            return 0

        # Mirror the live schema exactly (constraints + defaults preserved).
        live_create = get_create_sql(conn, "questions")
        archive_create = live_create.replace("questions", ARCHIVE_TABLE, 1)
        # CREATE TABLE IF NOT EXISTS using the mirrored definition.
        conn.execute(f"DROP TABLE IF EXISTS {ARCHIVE_TABLE}")
        conn.execute(archive_create)
        print(f"[info] (re)created {ARCHIVE_TABLE} mirroring questions schema.")

        already = 0
        if table_exists(conn, ARCHIVE_TABLE):
            already = conn.execute(
                f"SELECT COUNT(*) FROM {ARCHIVE_TABLE}"
            ).fetchone()[0]

        # Copy column list to be explicit and order-safe.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(questions)")]
        col_list = ", ".join(f'"{c}"' for c in cols)

        inserted = conn.execute(
            f"INSERT INTO {ARCHIVE_TABLE} ({col_list}) "
            f"SELECT {col_list} FROM questions WHERE source='generated'"
        ).rowcount
        print(f"[info] inserted {inserted} rows into {ARCHIVE_TABLE} "
              f"(archive now holds {already + inserted}).")

        if inserted != gen_count:
            conn.rollback()
            print(f"[err] insert count ({inserted}) != generated count "
                  f"({gen_count}); rolled back. Investigate before retry.",
                  file=sys.stderr)
            return 1

        deleted = conn.execute(
            "DELETE FROM questions WHERE source='generated'"
        ).rowcount
        print(f"[info] deleted {deleted} generated rows from questions.")

        if deleted != inserted:
            conn.rollback()
            print(f"[err] delete count ({deleted}) != insert count ({inserted}); "
                  f"rolled back.", file=sys.stderr)
            return 1

        conn.commit()

        # Verify final state.
        q_total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        q_corpus = conn.execute(
            "SELECT COUNT(*) FROM questions WHERE source='corpus'"
        ).fetchone()[0]
        q_gen = conn.execute(
            "SELECT COUNT(*) FROM questions WHERE source='generated'"
        ).fetchone()[0]
        a_total = conn.execute(
            f"SELECT COUNT(*) FROM {ARCHIVE_TABLE}"
        ).fetchone()[0]
        print("[ok] migration committed.")
        print(f"       questions        = {q_total} (corpus={q_corpus}, generated={q_gen})")
        print(f"       {ARCHIVE_TABLE} = {a_total}")
        if q_gen != 0:
            print("[warn] generated rows remain in questions!", file=sys.stderr)
            return 1
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
