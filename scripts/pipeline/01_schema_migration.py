"""Phase 1: Schema migration + exam_type casing normalization.

Adds new structured columns for enrichment data and normalizes exam_type
casing to a single canonical UPPERCASE form (see proposal Section 1-2).
Idempotent: safe to re-run.
"""
import sys
from db import get_conn

NEW_COLUMNS = [
    ("modules_json", "TEXT DEFAULT '[]'"),
    ("topic_keys_json", "TEXT DEFAULT '[]'"),
    ("skills_json", "TEXT DEFAULT '[]'"),
    ("worked_solution", "TEXT DEFAULT ''"),
    ("distractor_analysis", "TEXT DEFAULT ''"),
    ("difficulty", "TEXT DEFAULT ''"),
    ("difficulty_level", "TEXT DEFAULT ''"),
    ("question_type", "TEXT DEFAULT ''"),
    ("ocr_corrections_json", "TEXT DEFAULT '[]'"),
]

EXAM_TYPE_NORMALIZATION = {
    'engaa': 'ENGAA',
    'nsaa': 'NSAA',
    'tmua': 'TMUA',
    'nsaa_s2': 'NSAA_S2',
    'esat': 'ESAT',
}


def existing_columns(conn):
    cur = conn.execute("PRAGMA table_info(questions)")
    return {row[1] for row in cur.fetchall()}


def migrate_schema(conn):
    cols = existing_columns(conn)
    for name, ddl in NEW_COLUMNS:
        if name in cols:
            print(f"  skip (exists): {name}")
            continue
        conn.execute(f"ALTER TABLE questions ADD COLUMN {name} {ddl}")
        print(f"  added: {name}")
    conn.commit()


def normalize_exam_types(conn):
    for old, new in EXAM_TYPE_NORMALIZATION.items():
        cur = conn.execute("UPDATE questions SET exam_type = ? WHERE exam_type = ?", (new, old))
        print(f"  {old} -> {new}: {cur.rowcount} rows")
    conn.commit()


def main():
    conn = get_conn()
    print("Migrating schema...")
    migrate_schema(conn)
    print("Normalizing exam_type casing...")
    normalize_exam_types(conn)

    cur = conn.execute("SELECT exam_type, COUNT(*) FROM questions GROUP BY exam_type ORDER BY exam_type")
    print("\nFinal exam_type distribution:")
    total = 0
    for exam_type, count in cur.fetchall():
        print(f"  {exam_type}: {count}")
        total += count
    print(f"  TOTAL: {total}")

    expected_total = 1687
    if total != expected_total:
        print(f"WARNING: expected {expected_total} total rows, got {total}", file=sys.stderr)
        sys.exit(1)

    conn.close()
    print("\nPhase 1 complete.")


if __name__ == '__main__':
    main()
