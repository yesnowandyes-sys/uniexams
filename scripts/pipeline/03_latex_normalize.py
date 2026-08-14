#!/usr/bin/env python3
"""Phase 3: LaTeX normalization.

Wraps bare LaTeX commands (\\frac, \\times, x^{n}, etc.) in $...$ delimiters
for the lowercase-sourced exam sets (engaa/nsaa/tmua originally — now
normalized to ENGAA/NSAA/TMUA), which never had delimiters applied.

Approach: a forward-scanning, brace-balanced tokenizer (not a single fragile
regex) that:
  - Leaves text already inside $...$ or $$...$$ untouched (protected zones)
  - Leaves \\begin{...}...\\end{...} blocks untouched (diagram includes, not math)
  - Finds backslash-command runs (with balanced-brace args and chained
    ^/_ scripts and \\times/\\pm/etc connectors) and wraps each contiguous
    run in $...$
  - Also wraps bare token^{...}/token_{...} superscript/subscript idioms
    that have no leading backslash command (e.g. "m s^{-2}", "27^{2-n}")

This is a pure regex/parsing pass — no LLM calls, no cost. Runs on all rows;
skipped rows (already fully delimited, or no backslash present) are no-ops.
"""
import difflib
import json
import re
import sys

from db import get_conn

CONNECTOR_RE = re.compile(r"\s*(\\times|\\div|\\pm|\\cdot|[+\-=,])\s*")
PRECEDING_SCRIPT_RE = re.compile(r"([A-Za-z0-9)\]]+)([\^_])$")


def find_matching_brace(s: str, open_pos: int) -> int:
    depth = 0
    for i in range(open_pos, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def consume_command_span(s: str, i: int) -> int:
    """s[i] == '\\'. Consume the command, its balanced-brace args, chained
    ^/_ scripts, and connector-joined follow-on commands. Returns end index."""
    n = len(s)
    j = i + 1
    while j < n and s[j].isalpha():
        j += 1
    if j == i + 1:
        return min(i + 2, n)  # lone backslash / non-letter escape

    while True:
        advanced = False

        # optional single space then a balanced {..} argument
        k = j
        while k < n and s[k] == " ":
            k += 1
        if k < n and s[k] == "{":
            close = find_matching_brace(s, k)
            if close != -1:
                j = close + 1
                advanced = True
                continue

        # ^ or _ script
        if j < n and s[j] in "^_":
            k2 = j + 1
            if k2 < n and s[k2] == "{":
                close = find_matching_brace(s, k2)
                if close != -1:
                    j = close + 1
                    advanced = True
                    continue
            elif k2 < n and s[k2] == "\\":
                m = k2 + 1
                while m < n and s[m].isalpha():
                    m += 1
                if m > k2 + 1:
                    j = m
                    advanced = True
                    continue
            else:
                m = k2
                if m < n and s[m] == "-":
                    m += 1
                start_alnum = m
                while m < n and s[m].isalnum():
                    m += 1
                if m > start_alnum:
                    j = m
                    advanced = True
                    continue

        if advanced:
            continue

        # connector (\times, +, -, =, ,) joining to another backslash command
        m = CONNECTOR_RE.match(s, j)
        if m:
            k3 = m.end()
            if k3 < n and s[k3] == "\\":
                mm = k3 + 1
                while mm < n and s[mm].isalpha():
                    mm += 1
                if mm > k3 + 1:
                    j = mm
                    advanced = True
                    continue

        if not advanced:
            break
    return j


def try_consume_bare_script(s: str, i: int) -> int | None:
    """s[i] starts an alnum token; if immediately followed by ^/_ with a
    balanced-brace or simple argument, return the end index of that span.
    Otherwise None. Handles e.g. 's^{-2}', 'r^2', '27^{2-2n}'."""
    n = len(s)
    j = i
    while j < n and (s[j].isalnum() or s[j] in ")]"):
        j += 1
    if j == i or j >= n or s[j] not in "^_":
        return None
    k = j + 1
    if k < n and s[k] == "{":
        close = find_matching_brace(s, k)
        return close + 1 if close != -1 else None
    m = k
    if m < n and s[m] == "-":
        m += 1
    start = m
    while m < n and s[m].isalnum():
        m += 1
    return m if m > start else None


def protected_ranges(text: str) -> list[tuple[int, int]]:
    """Ranges (start, end) already inside $...$/$$...$$, \\(...\\), \\[...\\],
    or \\begin{}...\\end{} — i.e. already valid delimited LaTeX (or diagram
    includes), never wrap anything inside these."""
    ranges = []
    for pattern in (
        r"\$\$.*?\$\$|\$[^$]*\$",
        r"\\\(.*?\\\)",
        r"\\\[.*?\\\]",
        r"\\begin\{[^}]*\}.*?\\end\{[^}]*\}",
    ):
        for m in re.finditer(pattern, text, flags=re.DOTALL):
            ranges.append(m.span())
    ranges.sort()
    return ranges


def in_protected(pos: int, ranges: list[tuple[int, int]]) -> bool:
    for a, b in ranges:
        if a <= pos < b:
            return True
        if pos < a:
            break
    return False


def wrap_bare_latex(text: str) -> str:
    if not text or ("\\" not in text and not re.search(r"[A-Za-z0-9][\^_]", text)):
        return text

    ranges = protected_ranges(text)
    n = len(text)
    out = []
    buf = []

    def flush_buf():
        if buf:
            out.append("".join(buf))
            buf.clear()

    i = 0
    while i < n:
        if in_protected(i, ranges):
            flush_buf()
            end = next(b for a, b in ranges if a <= i < b)
            out.append(text[i:end])
            i = end
            continue

        if text[i] == "\\" and i + 1 < n and text[i + 1].isalpha():
            # pull back a preceding "token^" / "token_" prefix from the plain buffer
            joined = "".join(buf)
            pm = PRECEDING_SCRIPT_RE.search(joined)
            prefix = ""
            if pm:
                prefix = pm.group(0)
                buf.clear()
                if joined[: pm.start()]:
                    buf.append(joined[: pm.start()])
            flush_buf()
            span_end = consume_command_span(text, i)
            span = text[i:span_end]
            out.append("$" + prefix + span.strip() + "$")
            i = span_end
            continue

        if text[i].isalnum() or text[i] in ")]":
            end = try_consume_bare_script(text, i)
            if end is not None:
                flush_buf()
                out.append("$" + text[i:end] + "$")
                i = end
                continue

        buf.append(text[i])
        i += 1

    flush_buf()
    return "".join(out)


def needs_normalization(question_text: str, options_raw: str) -> bool:
    if "\\" in (question_text or "") and "$" not in (question_text or ""):
        return True
    try:
        opts = json.loads(options_raw or "{}")
    except json.JSONDecodeError:
        return False
    for v in opts.values() if isinstance(opts, dict) else []:
        if isinstance(v, str) and "\\" in v and "$" not in v:
            return True
    return False


def is_dollar_only_diff(original: str, transformed: str) -> bool:
    """True iff `transformed` differs from `original` only by inserting '$'
    characters — no existing character may be deleted, reordered, or
    replaced. Diff-based (not strip-and-compare) so it also works when
    `original` already contains legitimate '$' delimiters."""
    sm = difflib.SequenceMatcher(None, original, transformed, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert" and set(transformed[j1:j2]) <= {"$"}:
            continue
        return False
    return True


def safe_wrap(text: str) -> str:
    """wrap_bare_latex must only ever insert '$' characters, never delete or
    alter existing ones. A prior version of the tokenizer violated this
    (e.g. "3^{2-2n}" -> "$3^{2$-2n}", silently dropping the closing brace)
    and corrupted ~740 live questions. Any other kind of edit means the
    transform is untrusted for this input, so leave it unwrapped rather than
    risk corrupting question content."""
    wrapped = wrap_bare_latex(text)
    if not is_dollar_only_diff(text, wrapped):
        return text
    return wrapped


def normalize_options(options_raw: str) -> str:
    try:
        opts = json.loads(options_raw)
    except (json.JSONDecodeError, TypeError):
        return options_raw
    if not isinstance(opts, dict):
        return options_raw
    return json.dumps({k: safe_wrap(v) if isinstance(v, str) else v for k, v in opts.items()})


def main():
    conn = get_conn()
    rows = conn.execute("SELECT id, question_text, options FROM questions").fetchall()

    updated = 0
    for row in rows:
        qid, qtext, options = row["id"], row["question_text"], row["options"]
        if not needs_normalization(qtext, options):
            continue
        new_text = safe_wrap(qtext)
        new_options = normalize_options(options)
        if new_text != qtext or new_options != options:
            conn.execute(
                "UPDATE questions SET question_text = ?, options = ? WHERE id = ?",
                (new_text, new_options, qid),
            )
            updated += 1

    conn.commit()
    print(f"Phase 3: normalized LaTeX in {updated}/{len(rows)} questions")

    remaining = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE question_text LIKE '%\\%' AND question_text NOT LIKE '%$%'"
    ).fetchone()[0]
    print(f"Remaining question_text with bare backslash and no $ at all: {remaining}")
    conn.close()


if __name__ == "__main__":
    main()
