#!/usr/bin/env python3
"""
ESA-44 Part A — move generated questions into cold storage.

Moves every row with `source='generated'` from the main `questions` table into
a new `questions_generated_v1` table (identical schema, cloned from
`questions`). The moved rows stay queryable but are no longer served by the
website or used as exemplars. After this runs, `questions` contains only the
enriched corpus.

The operation is **idempotent**: re-running copies any newly-generated rows
into cold storage and deletes them from the main table, without touching rows
that were already moved. It is wrapped in a single transaction so the main
table and cold-storage table stay consistent.

Usage:
    python3 cold_store_generated.py [--db PATH] [--dry-run]

Reference: ESA-44 Part A.
"""

from __future__ import annotations

import argparse
import logging
import re
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger("cold_store")

DEFAULT_DB = "/home/ubuntu/.paperclip/esat-shared/data/questions.db"
COLD_TABLE = "questions_generated_v1"


def clone_schema_sql(con: sqlite3.Connection, new_table: str) -> str:
    """Return a CREATE TABLE statement for `new_table` mirroring `questions`.

    Cloning from sqlite_master keeps the cold-storage table in lock-step with
    the live schema (constraints, defaults, types) rather than hard-coding a
    copy that can drift.
    """
    row = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='questions'"
    ).fetchone()
    if not row or not row[0]:
        raise RuntimeError("could not read CREATE TABLE for 'questions'")
    base_sql = row[0]
    # The live table is declared as `CREATE TABLE questions (` (unquoted).
    # Emit `CREATE TABLE IF NOT EXISTS` so re-running is a safe no-op.
    new_sql, n = re.subn(
        r"CREATE\s+TABLE\s+questions\b",
        f"CREATE TABLE IF NOT EXISTS {new_table}",
        base_sql,
        count=1,
    )
    if n != 1:
        raise RuntimeError(
            f"unexpected questions schema; could not substitute table name: {base_sql!r}"
        )
    return new_sql


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--db", default=DEFAULT_DB, help="path to questions.db")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would happen, write nothing",
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    db = Path(args.db)
    if not db.exists():
        logger.error("database not found: %s", db)
        return 2

    con = sqlite3.connect(str(db))
    con.execute("PRAGMA foreign_keys=ON")
    try:
        total_before = con.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        gen_before = con.execute(
            "SELECT COUNT(*) FROM questions WHERE source='generated'"
        ).fetchone()[0]
        corpus_before = con.execute(
            "SELECT COUNT(*) FROM questions WHERE source='corpus'"
        ).fetchone()[0]
        logger.info(
            "before: total=%d corpus=%d generated=%d", total_before, corpus_before, gen_before
        )

        create_sql = clone_schema_sql(con, COLD_TABLE)
        logger.debug("clone schema:\n%s", create_sql)

        if args.dry_run:
            already = con.execute(
                f"SELECT COUNT(*) FROM {COLD_TABLE}"
            ).fetchone()[0] if _table_exists(con, COLD_TABLE) else 0
            logger.info(
                "[dry-run] would ensure table %s, copy %d generated row(s) into it, "
                "and delete them from questions",
                COLD_TABLE,
                gen_before,
            )
            logger.info("[dry-run] %s already holds %d row(s)", COLD_TABLE, already)
            return 0

        cur = con.cursor()
        cur.execute("BEGIN")
        cur.execute(create_sql)  # CREATE TABLE IF NOT EXISTS not used; clone is plain CREATE

        # Idempotent copy: only rows not already in cold storage.
        copied = cur.execute(
            f"""
            INSERT OR IGNORE INTO {COLD_TABLE}
            SELECT * FROM questions WHERE source='generated'
            """
        ).rowcount
        # Delete from main table only those we can confirm are in cold storage.
        deleted = cur.execute(
            f"""
            DELETE FROM questions
            WHERE source='generated'
              AND id IN (SELECT id FROM {COLD_TABLE})
            """
        ).rowcount
        con.commit()

        total_after = con.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        gen_after = con.execute(
            "SELECT COUNT(*) FROM questions WHERE source='generated'"
        ).fetchone()[0]
        corpus_after = con.execute(
            "SELECT COUNT(*) FROM questions WHERE source='corpus'"
        ).fetchone()[0]
        cold = con.execute(f"SELECT COUNT(*) FROM {COLD_TABLE}").fetchone()[0]
        logger.info(
            "after: questions total=%d corpus=%d generated=%d | %s=%d",
            total_after,
            corpus_after,
            gen_after,
            COLD_TABLE,
            cold,
        )
        logger.info("copied=%d deleted=%d", copied, deleted)

        # Sanity assertions.
        assert gen_after == 0, f"generated rows remain in questions: {gen_after}"
        assert corpus_after == corpus_before, "corpus count changed unexpectedly"
        assert total_after == corpus_after, "questions should hold only corpus now"
        logger.info("OK: questions now holds only the %d corpus rows.", corpus_after)
        return 0
    except Exception:
        con.rollback()
        logger.exception("cold-store failed; transaction rolled back")
        return 1
    finally:
        con.close()


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    return bool(
        con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
    )


def align_columns(con: sqlite3.Connection, name: str) -> list[str]:
    """Add to `name` any column present on `questions` but missing on `name`.

    Keeps the cold-storage table in lock-step with the live schema so that
    `SELECT *` copies keep working even after new columns (e.g. source_weight,
    sources) are added to `questions` later. Returns the names of added columns.
    SQLite ADD COLUMN forbids PK/UNIQUE, which the enrichment columns don't use.
    """
    q_info = {r[1]: r for r in con.execute("PRAGMA table_info(questions)")}
    cur_info = {r[1] for r in con.execute(f'PRAGMA table_info("{name}")')}
    added: list[str] = []
    for col_name, info in q_info.items():  # cid, name, type, notnull, dflt_value, pk
        if col_name in cur_info:
            continue
        _cid, _n, ctype, notnull, dflt, pk = info
        if pk:
            # Cannot add a PK via ALTER; skip (shouldn't happen for enrichment cols).
            continue
        parts = [f"ADD COLUMN {col_name}"]
        if ctype:
            parts.append(ctype)
        if notnull:
            parts.append("NOT NULL")
        if dflt is not None:
            parts.append(f"DEFAULT {dflt}")
        con.execute(f'ALTER TABLE "{name}" ' + " ".join(parts))
        added.append(col_name)
    return added


if __name__ == "__main__":
    sys.exit(main())
