#!/usr/bin/env python3
"""Phase 3c: Repair nested-delimiter corruption from an earlier Phase 3 run.

03_latex_normalize.py originally didn't treat \\(...\\) / \\[...\\] spans as
already-delimited, so it inserted extra $...$ around sub-expressions inside
them (e.g. "\\(_{20}^{40}\\text{Ca}^{2+}\\)" -> "\\(_{20}^{40}$\\text{Ca}^{2+}$\\)"),
producing invalid nested math delimiters. protected_ranges() now protects
these spans going forward; this script strips the erroneously-inserted '$'
characters from spans that already existed pre-Phase-3, in both
question_text and options.
"""
import json
import re

from db import get_conn

PAREN_SPAN_RE = re.compile(r"\\\(.*?\\\)", re.DOTALL)
BRACKET_SPAN_RE = re.compile(r"\\\[.*?\\\]", re.DOTALL)


def strip_dollars_in_delimited_spans(text: str) -> str:
    if not text or "\\(" not in text and "\\[" not in text:
        return text

    def repl(m):
        return m.group(0).replace("$", "")

    text = PAREN_SPAN_RE.sub(repl, text)
    text = BRACKET_SPAN_RE.sub(repl, text)
    return text


def fix_options(options_raw: str) -> str:
    try:
        opts = json.loads(options_raw)
    except (json.JSONDecodeError, TypeError):
        return options_raw
    if not isinstance(opts, dict):
        return options_raw
    return json.dumps(
        {k: strip_dollars_in_delimited_spans(v) if isinstance(v, str) else v for k, v in opts.items()}
    )


def main():
    conn = get_conn()
    rows = conn.execute("SELECT id, question_text, options FROM questions").fetchall()

    fixed = 0
    for row in rows:
        qid, qtext, options = row["id"], row["question_text"], row["options"]
        new_text = strip_dollars_in_delimited_spans(qtext)
        new_options = fix_options(options)
        if new_text != qtext or new_options != options:
            conn.execute(
                "UPDATE questions SET question_text = ?, options = ? WHERE id = ?",
                (new_text, new_options, qid),
            )
            fixed += 1

    conn.commit()
    print(f"Phase 3c: repaired nested-delimiter corruption in {fixed} rows")
    conn.close()


if __name__ == "__main__":
    main()
