#!/usr/bin/env python3
"""
Extract structured MCQ questions from ESAT past paper PDFs (ENGAA, NSAA, TMUA).

Converts PDF question papers + answer keys into structured JSON.
Uses pdftotext for text extraction and pymupdf only for image detection.

Usage:
    python3 extract_papers.py [INPUT_DIR] [OUTPUT_DIR] [--verbose] [--dry-run]
    python3 extract_papers.py --verbose
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    import pymupdf
except ImportError:
    os.system(f"{sys.executable} -m pip install pymupdf -q")
    import pymupdf

log = logging.getLogger("extract_papers")

DEFAULT_CORPUS = Path(__file__).resolve().parent.parent / "corpus"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "corpus" / "json"
MANIFEST_NAME = "format-manifest.json"
OPTION_LETTERS = set("ABCDEFGH")


# ── Helpers ──────────────────────────────────────────────────────────────────

def pdftotext(pdf_path: str, layout: bool = True) -> str:
    cmd = ["pdftotext", "-layout", pdf_path, "-"] if layout else ["pdftotext", pdf_path, "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.stdout if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.warning("pdftotext failed for %s: %s", pdf_path, e)
        return ""


def is_garbled(text: str) -> bool:
    if not text.strip():
        return True
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) < 10:
        return True
    # Check content after line 20 (skip header which may be clean)
    content_lines = [l for l in lines[20:] if l.strip()]
    if content_lines:
        bad = sum(1 for l in content_lines if sum(1 for c in l if ord(c) > 127) > max(2, len(l) * 0.15))
        if bad > len(content_lines) * 0.15:
            return True
    # Also check overall
    bad = sum(1 for l in lines if sum(1 for c in l if ord(c) > 127) > max(2, len(l) * 0.15))
    return bad > len(lines) * 0.3


def get_image_pages(pdf_path: str) -> set[int]:
    pages = set()
    try:
        doc = pymupdf.open(pdf_path)
        for i, page in enumerate(doc):
            if page.get_images(full=True):
                pages.add(i)
        doc.close()
    except Exception as e:
        log.warning("Image scan failed: %s", e)
    return pages


# ── Answer key parsing ───────────────────────────────────────────────────────

def parse_answer_key(text: str) -> dict[int, str]:
    answers: dict[int, str] = {}

    # Strategy 1: Number immediately adjacent to letter: "1G", "2B", "1F", "10 A"
    for m in re.finditer(r"(\d{1,3})\s*([A-H])(?:\s|$|\n)", text):
        n, letter = int(m.group(1)), m.group(2)
        if 1 <= n <= 200 and letter in OPTION_LETTERS:
            answers[n] = letter
    if len(answers) >= 5:
        return answers

    # Strategy 2: Q<number> newline letter
    answers.clear()
    for m in re.finditer(r"Q(\d{1,3})\s*\n\s*([A-H])\s*$", text, re.MULTILINE):
        n, letter = int(m.group(1)), m.group(2)
        if n >= 1:
            answers[n] = letter
    if len(answers) >= 5:
        return answers

    # Strategy 3: Layout — number then 2+ spaces then letter, on same line
    answers.clear()
    for m in re.finditer(r"(\d{1,3})\s{2,}([A-H])\s*$", text, re.MULTILINE):
        n, letter = int(m.group(1)), m.group(2)
        if 1 <= n <= 200 and letter in OPTION_LETTERS:
            answers[n] = letter
    if len(answers) >= 5:
        return answers

    # Strategy 4: Two-column table (numbers column, letters column)
    answers.clear()
    lines = text.strip().split("\n")
    nums, lets = [], []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if re.search(r"(?i)question|answer|key", s) and not re.match(r"^\d{1,3}[A-H]?$", s):
            continue
        if re.match(r"^(\d{1,3})$", s):
            nums.append((int(s), i))
        elif re.match(r"^([A-H])$", s):
            lets.append((s, i))
    if len(nums) >= 5 and len(lets) >= 5:
        if nums[-1][1] < lets[0][1]:  # all nums before all lets
            for i in range(min(len(nums), len(lets))):
                answers[nums[i][0]] = lets[i][0]
        else:
            used = set()
            for n, ni in nums:
                best, best_d = None, 999
                for li, (l, li_idx) in enumerate(lets):
                    if li in used:
                        continue
                    d = abs(ni - li_idx)
                    if d < best_d:
                        best_d = d
                        best = (li, l)
                if best and best_d <= 3:
                    answers[n] = best[1]
                    used.add(best[0])
    if len(answers) >= 5:
        return answers

    # Strategy 5: Q<number> with letter somewhere nearby
    answers.clear()
    for m in re.finditer(r"Q(\d{1,3})", text):
        n = int(m.group(1))
        chunk = text[m.start():m.start() + 40]
        lm = re.search(r"([A-H])\b", chunk[len(f"Q{n}"):])
        if lm and n >= 1:
            answers[n] = lm.group(1)
    return answers


# ── Question count detection ──────────────────────────────────────────────────

def find_question_count(text: str, ak: Optional[dict[int, str]], paper_type: str) -> int:
    if ak and len(ak) >= 5:
        return len(ak)
    for p in [r"(?:There are|are)\s+(\d+)\s+questions?\s+on this paper",
              r"(?:This paper contains?)\s+(\d+)\s+(?:multiple.choice )?questions?",
              r"(\d+)\s+questions?\.\s+Each question"]:
        m = re.search(p, text, re.I)
        if m:
            return int(m.group(1))
    m = re.search(r"(?:Each|each) part has (\d+) multiple.choice questions", text, re.I)
    if m:
        per_part = int(m.group(1))
        total_m = re.search(r"(?:contains?)\s+(\d+)\s+(?:multiple.choice )?questions", text, re.I)
        if total_m:
            return int(total_m.group(1))
        parts = re.findall(r"Part ([A-E])\b", text)
        return per_part * max(len(set(parts)), 2)
    return 0


# ── Content start ───────────────────────────────────────────────────────────

def find_content_start(lines: list[str]) -> int:
    """Find where question content begins. Skip header + table of contents."""
    # Strategy: find the FIRST "PART A ..." marker that is NOT in the
    # table of contents (no dots after it) or instructions.
    for i, line in enumerate(lines):
        s = line.strip()
        if re.match(r"^PART [A-E]\s+(?:Mathematics|Physics|Chemistry|Biology)", s, re.I):
            return max(0, i - 3)
        if s == "PART A" or s == "Part A":
            return max(0, i - 3)
        if re.match(r"^Paper [12]\s*$", s, re.I):
            return max(0, i - 3)
    # Fallback: look for first question number at left margin (col 0-2)
    for i, line in enumerate(lines):
        m = re.match(r"^(\s{0,2})(\d{1,2})\.?\s", line)
        if m:
            return max(0, i - 1)
    # Last resort: skip BLANK PAGE
    for i, line in enumerate(lines):
        if line.strip() == "BLANK PAGE":
            return i + 1
    return 0


# ── Question parsing ─────────────────────────────────────────────────────────

def parse_questions(text: str, expected: int, img_pages: set[int],
                    paper_type: str, year: str) -> list[dict]:
    if expected == 0:
        log.warning("Cannot determine expected count; auto-detecting")

    lines = text.split("\n")
    content_start = find_content_start(lines)

    # Phase 1: Collect all candidates
    candidates = []
    max_col = 3 if paper_type == "NSAA" else 2
    for i in range(content_start, len(lines)):
        line = lines[i]
        # Match: number at left margin, optionally followed by period (TMUA specimen: "1.")
        m = re.match(r"^(\s{0," + str(max_col) + r"})(\d{1,2})\.?\s", line)
        if m:
            col = len(m.group(1))
            num = int(m.group(2))
            if num >= 1 and (expected == 0 or num <= expected):
                candidates.append((i, num, col))
        # Also match number alone on line
        m = re.match(r"^(\s{0," + str(max_col) + r"})(\d{1,2})\.?\s*$", line)
        if m:
            col = len(m.group(1))
            num = int(m.group(2))
            if num >= 1 and (expected == 0 or num <= expected):
                candidates.append((i, num, col))

    log.debug("Content start L%d, %d candidates", content_start, len(candidates))

    if expected == 0:
        expected = max((n for _, n, _ in candidates), default=0)

    # Phase 2: Sequential selection with validation
    selected = {}
    search_from = 0
    for target in range(1, expected + 1):
        found = False
        for ci, (line_idx, num, col) in enumerate(candidates):
            if line_idx < search_from:
                continue
            if num == target:
                if _validate_question(lines, line_idx, target, col, paper_type):
                    selected[target] = line_idx
                    search_from = line_idx + 1
                    found = True
                else:
                    log.debug("Q%d at L%d col=%d rejected", target, line_idx, col)
                break
            if num > target + 10:
                break
        if not found:
            log.warning("Q%d: not found", target)

    # Phase 3: Extract
    questions = []
    sorted_nums = sorted(selected.keys())
    for idx, q_num in enumerate(sorted_nums):
        start = selected[q_num]
        end = selected[sorted_nums[idx + 1]] if idx + 1 < len(sorted_nums) else len(lines)
        block = lines[start:end]
        raw = "\n".join(l.rstrip() for l in block if l.strip()).strip()
        q_text, options = _split_question(block, q_num)
        has_diag = _check_diagram(start, end, lines, img_pages)
        questions.append({
            "question_number": q_num, "question_text": q_text,
            "has_diagram": has_diag, "options": options, "raw_text": raw,
        })

    return questions


def _validate_question(lines: list[str], idx: int, q_num: int,
                      col: int, paper_type: str) -> bool:
    """Is this candidate a real question start vs a page number or option value?"""
    # Reject if deeply indented (likely an option value or page number)
    max_col = 40 if paper_type == "NSAA" else 3
    if col >= max_col:
        return False

    # Check what's after the number on this line
    line = lines[idx]
    num_str = str(q_num)
    num_end = col + len(num_str)
    after = line[num_end:].strip() if num_end <= len(line) else ""

    # If there's substantial text after the number, it's a question
    if len(after) > 5:
        # But make sure it's not just "A" or "B" (option label)
        if not re.match(r"^[A-H]$", after):
            return True

    # Check next non-blank lines
    next_content = []
    for j in range(idx + 1, min(idx + 8, len(lines))):
        s = lines[j].strip()
        if s:
            next_content.append((j, s, len(lines[j]) - len(lines[j].lstrip())))
            if len(next_content) >= 3:
                break

    if not next_content:
        # Number alone, no following content — accept only if at very left
        return col <= 2

    # If next content starts with an option label (A-H), it's likely a question with options
    first_text, first_indent = next_content[0][1], next_content[0][2]
    if re.match(r"^[A-H]$", first_text):
        return True
    if re.match(r"^[A-H]\s{2,}", first_text) and first_indent >= 3:
        return True

    # Check for question-indicating language
    all_text = " ".join(nc[1] for nc in next_content[:2])
    q_words = re.compile(
        r"\b(what|which|how|find|calculate|determine|given|the |an? |"
        r"equation|function|value|result|probability|simplify|solve|"
        r"express|show|evaluate|consider|complete|choose|correct|"
        r"following|one of|where|for|that|sum|product|integral|"
        r"derivative|expression|inequality|graph|curve|sequence|series|"
        r"ratio|proportion|mean|median|variance|circle|triangle|"
        r"rectangle|parabola|polynomial|log|exponential|satisfy|"
        r"defined|set|solution|root|factor|simplify|object|particle|"
        r"block|car|train|spring|wire|light|sound|wave|ray|beam|"
        r"charge|current|voltage|resistance|energy|power|force|"
        r"acceleration|velocity|mass|density|pressure|temperature|"
        r"heat|work|gravitational|electric|magnetic|nuclear|atom|"
        r"molecule|cell|gene|protein|enzyme|organism|species|"
        r"ecosystem|population|evolution|mutation|chromosome|"
        r"reaction|compound|element|bond|ion|oxidation|reduction|"
        r"acid|base|solution|molar|concentration|equilibrium|"
        r"rate|constant|volume|area|length|distance|time|speed|"
        r"frequency|period|amplitude|wavelength|phase|angle|"
        r"coordinate|vector|matrix|transform|integral|differential|"
        r"gradient|divergence|curl|flux|field|potential|"
        r"continuous|differentiable|monotonic|strictly|increasing|"
        r"decreasing|positive|negative|integer|real|complex|"
        r"rational|irrational|prime|composite|divisible|remainder|"
        r"modulo|congruent|perpendicular|parallel|intersect|"
        r"tangent|normal|bisect|midpoint|centroid|circumcenter|"
        r"incenter|orthocenter|diameter|radius|chord|arc|sector|"
        r"cylinder|cone|sphere|cube|cuboid|prism|pyramid|"
        r"surface|cross.section|projection|reflection|rotation|"
        r"translation|symmetry|asymptote|intercept|turning|"
        r"stationary|inflection|maximum|minimum|critical|"
        r"domain|range|codomain|inverse|composite|identity|"
        r"bijection|injection|surjection|relation|equivalence|"
        r"partition|subset|union|intersection|complement|empty|"
        r"universal|power|cartesian|product|ordered|pair|triple|"
        r"tuple|sequence|series|convergence|divergence|limit|"
        r"tends|approaches|converges|diverges|nth|first|second|"
        r"third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
        r"half|quarter|third|fifth|twice|three times|four times|"
        r"per|each|every|all|any|some|none|both|either|neither)\b", re.I)
    if q_words.search(all_text):
        return True
    if len(all_text) > 30:
        return True

    # Bare number at very left margin — likely a question start
    if col <= 1:
        return True

    return False


def _split_question(block: list[str], q_num: int) -> tuple[str, dict[str, str]]:
    q_parts, options = [], {}
    in_options, current_letter = False, None

    for line in block:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == str(q_num) or stripped == str(q_num) + '.':
            continue
        if re.match(r"^©\s*UCLES", stripped) or stripped in ("[Turn over]", "BLANK PAGE"):
            continue

        # Option: indent 0-8, letter, 1+ spaces, text
        # TMUA: indent 4, letter, 1 space ("    A −"), ENGAA: indent 4, 3 spaces ("    A   £27")
        opt_m = re.match(r"^(\s{0,8})([A-H])\s{2,}(.+)$", line)
        if not opt_m:
            # Try 1-space variant (TMUA style, must have indent >= 3)
            opt_m = re.match(r"^(\s{3,8})([A-H])\s{1}(.+)$", line)
        if opt_m and opt_m.group(2) in OPTION_LETTERS:
            in_options = True
            current_letter = opt_m.group(2)
            options[current_letter] = opt_m.group(3).strip()
            continue

        # Option label alone (indent 0-8)
        opt_a = re.match(r"^(\s{0,8})([A-H])\s*$", line)
        if opt_a and opt_a.group(2) in OPTION_LETTERS:
            in_options = True
            current_letter = opt_a.group(2)
            options.setdefault(current_letter, "")
            continue

        if in_options and current_letter:
            indent = len(line) - len(line.lstrip())
            if indent >= 3:
                options[current_letter] = (options.get(current_letter, "") + " " + stripped).strip()
            else:
                q_parts.append(stripped)
        else:
            q_parts.append(stripped)

    q_text = re.sub(r"\s+", " ", " ".join(q_parts)).strip()
    return q_text, options


def _check_diagram(start, end, lines, img_pages):
    if not img_pages:
        return False
    page = sum(1 for i in range(min(start, len(lines))) if lines[i] == "\f")
    for i in range(start, min(end, len(lines))):
        if lines[i] == "\f":
            page += 1
        if page in img_pages:
            return True
    return False


# ── Manifest ─────────────────────────────────────────────────────────────────

def load_manifest(corpus_dir: Path) -> list[dict]:
    p = corpus_dir / MANIFEST_NAME
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return build_manifest(corpus_dir)


def build_manifest(corpus_dir: Path) -> list[dict]:
    entries = []
    for sd in sorted(corpus_dir.iterdir()):
        if not sd.is_dir():
            continue
        for pdf in sorted(sd.glob("*.pdf")):
            entries.append(_parse_fn(pdf.name, sd.name))
    return entries


def _parse_fn(fn, subdir):
    m = re.match(r"([A-Z]+)_(\d{4}|specimen)_S1_(QuestionPaper|AnswerKey)\.pdf", fn, re.I)
    if m:
        return {"filename": fn, "paper_type": m.group(1).upper(), "year": m.group(2),
                "section": "Section1", "kind": m.group(3), "subdir": subdir}
    m = re.match(r"TMUA-(?:early-)?(\d{4}|specimen)-paper-(\d)\.pdf", fn, re.I)
    if m:
        return {"filename": fn, "paper_type": "TMUA", "year": m.group(1),
                "section": f"Paper{m.group(2)}", "kind": "QuestionPaper", "subdir": subdir}
    return {"filename": fn, "paper_type": subdir.upper(), "year": "unknown",
            "section": "unknown", "kind": "unknown", "subdir": subdir}


# ── Main ─────────────────────────────────────────────────────────────────────

def process_paper(qp, ak_entry, corpus_dir):
    fn, pt, year, section = qp["filename"], qp["paper_type"], qp["year"], qp["section"]
    subdir = qp.get("subdir", pt.lower())
    pdf_path = corpus_dir / subdir / fn
    if not pdf_path.exists():
        pdf_path = corpus_dir / fn
    if not pdf_path.exists():
        return {"file": fn, "error": "file not found", "questions": 0}

    log.info("Processing %s (%s %s %s)", fn, pt, year, section)
    text = pdftotext(str(pdf_path), layout=True)
    if not text.strip() or is_garbled(text):
        log.warning("  Garbled/empty — skipping")
        return {"file": fn, "error": "garbled/empty text", "questions": 0}

    img_pages = get_image_pages(str(pdf_path))
    if img_pages:
        log.info("  %d image pages", len(img_pages))

    ak = None
    if ak_entry:
        ak_fn, ak_sd = ak_entry["filename"], ak_entry.get("subdir", pt.lower())
        ak_path = corpus_dir / ak_sd / ak_fn
        if not ak_path.exists():
            ak_path = corpus_dir / ak_fn
        if ak_path.exists():
            ak = parse_answer_key(pdftotext(str(ak_path), layout=True))
            log.info("  AK: %d answers", len(ak))

    expected = find_question_count(text, ak, pt)
    log.info("  Expected: %d", expected)
    questions = parse_questions(text, expected, img_pages, pt, year)
    log.info("  Extracted: %d", len(questions))

    errors = []
    for q in questions:
        if not q["question_text"].strip():
            errors.append(f"Q{q['question_number']}: empty text")
        if not q["options"]:
            errors.append(f"Q{q['question_number']}: no options")

    sec_tag = section.upper().replace("SECTION", "S").replace("PAPER", "P").replace(" ", "")
    out_qs = []
    for q in questions:
        correct = ak.get(q["question_number"]) if ak else None
        out_qs.append({
            "id": f"{pt}-{year}-{sec_tag}-Q{q['question_number']}",
            "year": year, "paper": pt, "section": sec_tag,
            "question_number": q["question_number"],
            "question_text": q["question_text"],
            "has_diagram": q["has_diagram"],
            "options": q["options"],
            "correct_answer": correct,
            "raw_text": q["raw_text"],
        })

    return {"file": fn, "paper_type": pt, "year": year, "section": sec_tag,
            "expected": expected, "questions_extracted": len(out_qs),
            "answer_key_count": len(ak) if ak else 0,
            "errors": errors, "image_pages": len(img_pages),
            "questions": out_qs}


def main():
    ap = argparse.ArgumentParser(description="Extract MCQ questions from ESAT past papers")
    ap.add_argument("input_dir", nargs="?", default=str(DEFAULT_CORPUS))
    ap.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT))
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(format="%(levelname)s: %(message)s",
                        level=logging.DEBUG if args.verbose else logging.INFO)

    corpus_dir, output_dir = Path(args.input_dir).resolve(), Path(args.output_dir).resolve()
    log.info("Corpus: %s | Output: %s", corpus_dir, output_dir)

    manifest = load_manifest(corpus_dir)
    qp_entries = [e for e in manifest if e["kind"] == "QuestionPaper"]
    ak_map = {(e["paper_type"], e["year"], e["section"]): e
              for e in manifest if e["kind"] == "AnswerKey"}
    qp_entries.sort(key=lambda e: ({"ENGAA": 0, "NSAA": 1, "TMUA": 2}.get(e["paper_type"], 99),
                                    str(e["year"]), e.get("section", "")))

    results, total_q, total_err, issues = [], 0, 0, []
    for qp in qp_entries:
        ak = ak_map.get((qp["paper_type"], qp["year"], qp["section"]))
        r = process_paper(qp, ak, corpus_dir)
        results.append(r)
        n_q = r.get("questions_extracted", 0)
        total_q += n_q
        errs = r.get("errors", [])
        total_err += len(errs)
        if r.get("error") or errs:
            issues.append(r.get("file", "?"))

        if not args.dry_run and n_q > 0:
            pt_l = qp["paper_type"].lower()
            yr = qp["year"]
            st = qp["section"].upper().replace("SECTION", "S").replace("PAPER", "P").replace(" ", "")
            (output_dir / pt_l).mkdir(parents=True, exist_ok=True)
            out_f = output_dir / pt_l / f"{yr}_{st.lower()}.json"
            with open(out_f, "w", encoding="utf-8") as f:
                json.dump({"source_file": qp["filename"], "paper_type": qp["paper_type"],
                           "year": yr, "section": qp["section"],
                           "total_questions": n_q, "questions": r["questions"]},
                          f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 70}\nEXTRACTION SUMMARY\n{'=' * 70}")
    print(f"Papers: {len(results)} | Questions: {total_q} | Errors: {total_err}")
    if issues:
        print(f"\nPapers with issues ({len(issues)}):")
        for f in issues:
            print(f"  - {f}")
    print(f"\n{'File':<45} {'Exp':>4} {'Got':>4} {'AK':>4} {'Err':>4}")
    print("-" * 70)
    for r in results:
        fn = r.get("file", "?")
        if r.get("error"):
            print(f"{fn:<45} {'ERR':>4} {r['error']}")
        else:
            print(f"{fn:<45} {r.get('expected', 0):>4} {r.get('questions_extracted', 0):>4} "
                  f"{r.get('answer_key_count', 0):>4} {len(r.get('errors', [])):>4}")

    if not args.dry_run:
        import datetime
        summary = {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "corpus_dir": str(corpus_dir), "output_dir": str(output_dir),
            "total_papers": len(results), "total_questions": total_q,
            "total_errors": total_err,
            "papers": [{"file": r.get("file"), "paper_type": r.get("paper_type"),
                        "year": r.get("year"), "section": r.get("section"),
                        "expected": r.get("expected", 0),
                        "extracted": r.get("questions_extracted", 0),
                        "answer_key_count": r.get("answer_key_count", 0),
                        "errors": r.get("errors", []), "error": r.get("error")}
                       for r in results],
        }
        with open(corpus_dir / "extraction-summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\nSummary: {corpus_dir / 'extraction-summary.json'}")
    else:
        print("\n(dry run)")


if __name__ == "__main__":
    main()
