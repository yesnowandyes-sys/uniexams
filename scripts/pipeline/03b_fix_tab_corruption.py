#!/usr/bin/env python3
"""Phase 3b: Repair pre-existing JSON-escaping corruption in question_text.

Some source records were produced with single-backslash JSON strings like
"...\text{Ca}..." instead of properly escaped "...\\text{Ca}...". When
json.loads() parsed those, "\t" was interpreted as the JSON escape for TAB
(0x09), silently eating the backslash and 't' and leaving a literal tab
character followed by "ext{Ca}" — i.e. "\text" became TAB+"ext".

Confirmed corrupted commands (all start with \\t): \\text, \\theta, \\times, \\tan.
Fix: replace the literal TAB character with the two characters "\\t", which
reconstructs the original command exactly. Affects only question_text (26
rows, 93 occurrences) — options/worked_solution/distractor_analysis are clean.

Must run before (or be followed by a re-run of) 03_latex_normalize.py so the
now-legible \\text/\\theta/\\times/\\tan commands get $ delimiters.
"""
from db import get_conn


def main():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, question_text FROM questions WHERE question_text LIKE '%' || char(9) || '%'"
    ).fetchall()

    fixed = 0
    for row in rows:
        qid, qtext = row["id"], row["question_text"]
        new_text = qtext.replace("\t", "\\t")
        if new_text != qtext:
            conn.execute("UPDATE questions SET question_text = ? WHERE id = ?", (new_text, qid))
            fixed += 1

    conn.commit()
    print(f"Phase 3b: repaired tab-corrupted LaTeX commands in {fixed} question_text rows")

    remaining = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE question_text LIKE '%' || char(9) || '%'"
    ).fetchone()[0]
    print(f"Remaining rows with raw tab characters: {remaining}")
    conn.close()


if __name__ == "__main__":
    main()
