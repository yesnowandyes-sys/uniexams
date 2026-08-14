"""Phase 2: Extract structured data from existing enrichment JSON (no LLM).

Populates: difficulty, difficulty_level, difficulty_score, question_type,
ocr_corrections_json, worked_solution, distractor_analysis, modules_json,
topic_keys_json.

Idempotent: only touches rows where the target column is still at its
default/empty value, so re-running after Phase 4 backfill only fills gaps.
"""
import json
import re

from db import get_conn
from taxonomy import build_topic_keys


def extract_sections(markdown: str) -> dict:
    sections = {}
    parts = re.split(r'^## (.+)$', markdown, flags=re.MULTILINE)
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ''
        sections[header] = content
    return sections


def extract_worked_solution(markdown: str) -> str:
    sections = extract_sections(markdown)
    sol = sections.get('Worked Solution', '')
    sol = re.sub(r'\n*The correct answer is \*\*[A-H]\*\*\.?\s*$', '', sol, flags=re.MULTILINE)
    return sol.strip()


def extract_distractor_analysis(markdown: str) -> str:
    sections = extract_sections(markdown)
    return sections.get('Distractor Analysis', '')


def get_modules_json(enrichment: dict) -> str:
    tc = enrichment.get('topic_classification') or {}
    mc = (tc.get('module_code') or '').strip()

    if ' / ' in mc:
        codes = [c.strip() for c in mc.split(' / ')]
        return json.dumps([c for c in codes if c and c.upper() != 'N/A'])
    if not mc or mc.upper() in ('N/A', 'OUT_OF_SPEC'):
        return json.dumps([])
    return json.dumps([mc])


def get_topic_keys_json(enrichment: dict) -> str:
    # NOTE: fixed 2026-08-14 — the previous version embedded the full decimal
    # topic_code (e.g. "P2.2", "M5.18") into the topic_key, producing values
    # like "PHYS.P2.2" that don't match the existing topic_key column
    # convention (always integer topic-level, e.g. "MATHS1.M4"). Now truncates
    # to the topic-level code via taxonomy.build_topic_keys(), falling back to
    # module_code when topic_code is unusable (Appendix C).
    tc = enrichment.get('topic_classification') or {}
    topic_code = (tc.get('topic_code') or '').strip()
    module_code = (tc.get('module_code') or '').strip()
    return json.dumps(build_topic_keys(topic_code, module_code))


def bulk_sql_extraction(conn):
    cur = conn.execute("""
        UPDATE questions SET
            difficulty = CAST(json_extract(enrichment, '$.difficulty_rating') AS TEXT) || '/10',
            difficulty_level = json_extract(enrichment, '$.difficulty_category'),
            difficulty_score = json_extract(enrichment, '$.difficulty_rating')
        WHERE json_extract(enrichment, '$.difficulty_rating') IS NOT NULL
        AND difficulty = ''
    """)
    print(f"  difficulty/difficulty_level/difficulty_score: {cur.rowcount} rows")

    cur = conn.execute("""
        UPDATE questions SET
            question_type = json_extract(enrichment, '$.topic_classification.question_type')
        WHERE json_extract(enrichment, '$.topic_classification.question_type') IS NOT NULL
        AND question_type = ''
    """)
    print(f"  question_type: {cur.rowcount} rows")

    cur = conn.execute("""
        UPDATE questions SET
            ocr_corrections_json = COALESCE(json_extract(enrichment, '$.ocr_corrections'), '[]')
        WHERE ocr_corrections_json = '[]'
        AND enrichment IS NOT NULL AND enrichment != ''
    """)
    print(f"  ocr_corrections_json: {cur.rowcount} rows")
    conn.commit()


def python_extraction(conn):
    rows = conn.execute("""
        SELECT id, enrichment FROM questions
        WHERE enrichment IS NOT NULL AND enrichment != ''
        AND (worked_solution = '' OR modules_json = '[]' OR topic_keys_json = '[]')
    """).fetchall()

    updated = 0
    skipped_bad_json = 0
    for qid, enrichment_raw in rows:
        try:
            enrichment = json.loads(enrichment_raw)
        except json.JSONDecodeError:
            skipped_bad_json += 1
            continue

        markdown = enrichment.get('markdown', '') or ''
        worked_solution = extract_worked_solution(markdown) if markdown else ''
        distractor_analysis = extract_distractor_analysis(markdown) if markdown else ''
        modules_json = get_modules_json(enrichment)
        topic_keys_json = get_topic_keys_json(enrichment)

        conn.execute("""
            UPDATE questions SET
                worked_solution = CASE WHEN worked_solution = '' THEN ? ELSE worked_solution END,
                distractor_analysis = CASE WHEN distractor_analysis = '' THEN ? ELSE distractor_analysis END,
                modules_json = CASE WHEN modules_json = '[]' THEN ? ELSE modules_json END,
                topic_keys_json = CASE WHEN topic_keys_json = '[]' THEN ? ELSE topic_keys_json END
            WHERE id = ?
        """, (worked_solution, distractor_analysis, modules_json, topic_keys_json, qid))
        updated += 1

    conn.commit()
    print(f"  worked_solution/distractor_analysis/modules_json/topic_keys_json: {updated} rows updated, {skipped_bad_json} bad JSON skipped")


def fix_topic_keys_all(conn):
    """One-off repair pass: recompute topic_keys_json for every row that has
    enrichment, overwriting any previously-written value. Needed because an
    earlier version of this script embedded decimal topic_codes (e.g. 'P2.2')
    into topic_keys_json instead of truncating to the topic level ('P2')."""
    rows = conn.execute("""
        SELECT id, enrichment FROM questions
        WHERE enrichment IS NOT NULL AND enrichment != ''
    """).fetchall()
    fixed = 0
    for qid, enrichment_raw in rows:
        try:
            enrichment = json.loads(enrichment_raw)
        except json.JSONDecodeError:
            continue
        topic_keys_json = get_topic_keys_json(enrichment)
        conn.execute("UPDATE questions SET topic_keys_json = ? WHERE id = ?", (topic_keys_json, qid))
        fixed += 1
    conn.commit()
    print(f"  topic_keys_json repaired for {fixed} rows")


def main():
    conn = get_conn()
    print("Bulk SQL extraction...")
    bulk_sql_extraction(conn)
    print("Python markdown/classification extraction...")
    python_extraction(conn)
    print("Repairing topic_keys_json (topic-level truncation fix)...")
    fix_topic_keys_all(conn)

    print("\nCompleteness check:")
    for col, default in [
        ('difficulty', "''"), ('difficulty_level', "''"), ('question_type', "''"),
        ('worked_solution', "''"), ('distractor_analysis', "''"),
        ('modules_json', "'[]'"), ('topic_keys_json', "'[]'"),
    ]:
        total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        empty = conn.execute(f"SELECT COUNT(*) FROM questions WHERE {col} = {default}").fetchone()[0]
        print(f"  {col}: {total - empty}/{total} populated")

    conn.close()
    print("\nPhase 2 complete.")


if __name__ == '__main__':
    main()
