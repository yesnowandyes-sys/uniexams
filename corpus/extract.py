#!/usr/bin/env python3
"""
Extract structured MCQ questions from ESAT past papers (ENGAA, NSAA, TMUA).

Uses pdftotext -layout to preserve column positions, making it possible to
distinguish question numbers (left-aligned) from option values (indented).

Usage:
    python3 extract.py [--paper X] [--year Y] [--verbose] [--dry-run]
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:
    print("ERROR: pip install pymupdf"); sys.exit(1)

CORPUS_DIR = Path(__file__).parent
MANIFEST = CORPUS_DIR / "format-manifest.json"
OUTPUT_DIR = CORPUS_DIR / "extracted"

log = logging.getLogger("extract")
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
if "--verbose" in sys.argv or "-v" in sys.argv:
    log.setLevel(logging.DEBUG)

OPTION_LABELS = set("ABCDEFGH")


def pdftotext_layout(pdf_path: str) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True, text=True, timeout=60,
    )
    return result.stdout if result.returncode == 0 else ""


def pdftotext_plain(pdf_path: str) -> str:
    result = subprocess.run(
        ["pdftotext", pdf_path, "-"],
        capture_output=True, text=True, timeout=60,
    )
    return result.stdout if result.returncode == 0 else ""


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


def is_scanned_pdf(text: str) -> bool:
    """Detect if pdftotext output is garbage from a scanned PDF."""
    lines = text.split("\n")
    if len(lines) < 10:
        return True
    # Check proportion of lines with significant non-ASCII content
    bad_lines = sum(1 for l in lines if sum(1 for c in l if ord(c) > 127) > 2)
    return bad_lines > len(lines) * 0.1  # >10% of lines have mojibake


def parse_answer_key(text: str) -> dict[str, str]:
    answers = {}
    # Format 1: Q<number> <letter> inline
    for m in re.finditer(r"Q(\d+)\s+([A-H])\b", text):
        answers[m.group(1)] = m.group(2)
    if len(answers) >= 5:
        return answers
    # Format 4: layout format "1          G" (number, whitespace, letter)
    # May have two numbers per line (two-column layout): "  1  F  28  E"
    for line in text.split("\n"):
        for m in re.finditer(r"(\d{1,3})\s{2,}([A-H])", line):
            answers[m.group(1)] = m.group(2)
    if len(answers) >= 5:
        return answers
    # Format 3: Q<number> newline <letter>
    for m in re.finditer(r"Q(\d+)\s*\n\s*([A-H])\s*$", text, re.MULTILINE):
        answers[m.group(1)] = m.group(2)
    if len(answers) >= 5:
        return answers
    # Format 2: Two-column — numbers then letters
    lines = text.strip().split("\n")
    answer_start = next((i for i, l in enumerate(lines)
                        if re.search(r"answer", l, re.I)), 0)
    nums, lets, phase = [], [], "nums"
    for line in lines[answer_start:]:
        s = line.strip()
        if not s:
            continue
        if re.match(r"^answer", s, re.I):
            phase = "lets"; continue
        if re.match(r"^\d{1,3}$", s) and phase == "nums":
            nums.append(int(s))
        elif re.match(r"^[A-H]$", s) and phase == "lets":
            lets.append(s)
    # Fallback: find blocks
    if len(nums) < 5:
        nums, lets = [], []
        in_n = False
        for line in lines:
            s = line.strip()
            if not s: continue
            if re.match(r"^\d{1,3}$", s):
                if not lets: in_n = True; nums.append(int(s))
                elif in_n: nums.append(int(s))
            elif re.match(r"^[A-H]$", s):
                in_n = False; lets.append(s)
            elif lets: break
    for i in range(min(len(nums), len(lets))):
        answers[str(nums[i])] = lets[i]
    return answers


def find_expected_count(text: str, ak: dict | None, paper_type: str = "") -> int:
    if ak: return len(ak)
    for p in [r"(?:contains?|are)\s+(\d+)\s+.*?questions?",
              r"(\d+)\s+questions?\.", r"There are (\d+) questions",
              r"Each part has (\d+)", r"part has (\d+) multiple-choice"]:
        m = re.search(p, text, re.I)
        if m:
            n = int(m.group(1))
            # NSAA: each part has N questions, paper has all parts printed
            if "Each part has" in m.group(0) or "part has" in m.group(0):
                if paper_type == "NSAA":
                    if n == 18:
                        return n * 5  # 2016-2019: 5 parts (A-E)
                    elif n == 20:
                        return n * 4  # 2020+: 4 parts (A-D)
                return n
            return n
    return 0


def parse_questions_layout(text: str, expected: int, ak: dict | None,
                           img_pages: set[int], paper_type: str = "") -> tuple[list[dict], list[str]]:
    """
    Parse questions from layout-preserving pdftotext output.
    
    Key insight: question numbers appear at column 0-10 (left margin).
    Option values appear at column 10+ (indented).
    """
    lines = text.split("\n")
    questions = []
    errors = []

    if expected == 0:
        return questions, ["Cannot determine expected question count"]

    # Step 1: Find all candidate question starts
    # A question start is a line where:
    #   - A number 1..N appears at column 0-8
    #   - The number is followed by question text (either same line or next non-blank)
    #   - The number is NOT at column 10+ (those are option values)
    
    candidates = []  # (line_idx, question_number, column)
    for i, line in enumerate(lines):
        m = re.match(r"^(\s{0,8})(\d{1,2})\.?\s", line)
        if m:
            col = len(m.group(1))
            num = int(m.group(2))
            if 1 <= num <= expected:
                candidates.append((i, num, col))
            continue
        # Also match number alone on line at left margin
        m = re.match(r"^(\s{0,8})(\d{1,2})\.?\s*$", line)
        if m:
            col = len(m.group(1))
            num = int(m.group(2))
            if 1 <= num <= expected:
                candidates.append((i, num, col))

    log.debug("Found %d candidates for %d expected questions", len(candidates), expected)

    # Step 2: Select the correct sequence of question starts
    # Walk through candidates sequentially: accept the first candidate for Q1,
    # then the first candidate for Q2 that appears AFTER Q1's position, etc.
    selected = {}
    search_from = 0
    cand_idx = 0
    
    for target_q in range(1, expected + 1):
        found = False
        # Look for candidates with matching question number after search_from
        for ci in range(cand_idx, len(candidates)):
            line_idx, num, col = candidates[ci]
            if line_idx < search_from:
                continue
            if num == target_q:
                # Validate: check that what follows looks like question text
                if _looks_like_question_start(lines, line_idx, target_q, col, paper_type=paper_type):
                    selected[target_q] = line_idx
                    search_from = line_idx + 1
                    cand_idx = ci + 1
                    found = True
                    break
                else:
                    log.debug("Q%d at L%d col=%d rejected", target_q, line_idx, col)
                    # Don't advance cand_idx — keep searching
                    continue
            # If we've passed the target number (num > target_q) by a lot,
            # the target might not be findable at the right position
            if num > target_q + 5:
                break
        
        if not found:
            # Fallback: take first matching number after search_from, regardless of validation
            for ci in range(cand_idx, len(candidates)):
                line_idx, num, col = candidates[ci]
                if line_idx < search_from:
                    continue
                if num == target_q:
                    selected[target_q] = line_idx
                    search_from = line_idx + 1
                    cand_idx = ci + 1
                    errors.append(f"Q{target_q}: unvalidated (col={col})")
                    found = True
                    break
            if not found:
                errors.append(f"Q{target_q}: MISSING")

    # Step 3: Extract text for each question
    sorted_qnums = sorted(selected.keys())
    for idx, q_num in enumerate(sorted_qnums):
        start = selected[q_num]
        end = selected[sorted_qnums[idx + 1]] if idx + 1 < len(sorted_qnums) else len(lines)
        block = lines[start:end]

        # Get the question text and options
        q_text, options = _extract_q_text_and_options(block, q_num)
        raw = "\n".join(l.rstrip() for l in block if l.strip()).strip()

        has_diag = _check_diag(start, lines, img_pages)
        correct = ak.get(str(q_num)) if ak else None

        questions.append({
            "question_number": q_num,
            "question_text": q_text,
            "has_diagram": has_diag,
            "options": options,
            "correct_answer": correct,
            "raw_text": raw,
        })

    return questions, errors


def _looks_like_question_start(lines: list[str], idx: int, q_num: int, col: int, paper_type: str = "") -> bool:
    """
    Validate that this is a real question start, not an option value.
    """
    # Column heuristic: for NSAA multi-part papers, be more lenient
    # For other papers, numbers at col >= 15 are likely option values
    max_col = 15
    if col >= max_col:
        return False

    # Check what follows the number on this line
    line = lines[idx]
    # If the number is followed by question text on the same line (e.g., "1   The admission...")
    after_num = re.sub(r"^\s*\d{1,2}\.?\s*", "", line).strip()
    if after_num and len(after_num) > 5:
        # Check it's not just an option label (e.g., "A   3/4" or "A 5" at end of line)
        # But allow full sentences starting with A/An/The followed by longer text
        if re.match(r"^[A-H]   +\d", after_num):
            return False  # option label + fraction/number value (multi-space indent)
        # "A 2.40 g" is a sentence, not an option. Options are typically short values.
        # An option label would be like "A 5" alone or "A 3/4" or "A –2".
        if re.match(r"^[A-H] [\d–-][\d./ ]*$", after_num):
            return False  # option label + short numeric value
        return True

    # Check the next few non-blank lines
    next_content = []
    for j in range(idx + 1, min(idx + 6, len(lines))):
        s = lines[j].strip()
        if s:
            next_content.append(s)
            if len(next_content) >= 2:
                break

    if not next_content:
        return False

    first = next_content[0]
    
    # If the next content is just an option letter on its own line,
    # this might be the start of options (meaning the question text was on the same
    # line as the number, or there's no question text)
    if re.match(r"^[A-H]$", first):
        # Check if there's meaningful text after: option labels + values = valid
        # This is a borderline case. Accept if column is very left (0-2)
        return col <= 3

    # If next content is a short number at a rightward column, it's an option value
    m = re.match(r"^(\s*)(\d{1,3})\s*$", lines[idx + 1]) if idx + 1 < len(lines) else None
    if m and len(m.group(1)) >= 8:
        # Deeply indented number = option value
        return False

    # If next content contains question-like text, accept
    q_words = re.compile(
        r"\b(what|which|how|find|calculate|determine|given|the |an? |"
        r"equation|function|value|result|probability|simplify|solve|"
        r"express|show|evaluate|consider|describe|state|complete|choose|"
        r"true|false|correct|incorrect|following|one of)\b",
        re.I,
    )
    # Check first and second content lines
    for nc in next_content:
        if len(nc) > 15 or q_words.search(nc):
            return True

    # Accept if the number is at the very left margin (col 0-2) — likely a page-start question
    if col <= 2:
        return True

    return False


def _extract_q_text_and_options(block: list[str], q_num: int) -> tuple[str, list[str]]:
    """Extract question text and options from a question block."""
    q_parts = []
    options = []
    in_options = False
    current_option_letter = None

    for line in block:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip the question number line itself (with optional period)
        if re.match(r"^\s*" + str(q_num) + r"\.?\s*$", stripped):
            continue

        # Check for option label at left indent (col 0-6 typically)
        opt_match = re.match(r"^(\s{0,6})([A-H])\s{2,}(.+)$", line)
        if opt_match:
            in_options = True
            letter = opt_match.group(2)
            text = opt_match.group(3).strip()
            options.append(f"{letter}: {text}")
            current_option_letter = letter
            continue

        # Check for option label alone on line (col 0-6)
        opt_alone = re.match(r"^(\s{0,6})([A-H])\s*$", line)
        if opt_alone:
            in_options = True
            current_option_letter = opt_alone.group(2)
            continue

        if in_options and current_option_letter:
            # This could be option text (continuation) or start of new question
            # Check indent: option text is typically indented
            indent = len(line) - len(line.lstrip())
            if indent >= 6:
                # Likely option text continuation
                if options:
                    options[-1] += " " + stripped
            else:
                # Left-aligned text after options — likely not part of this question
                # But could be multi-paragraph question text
                q_parts.append(stripped)
        else:
            q_parts.append(stripped)

    q_text = "\n".join(q_parts).strip()
    return q_text, options


def _check_diag(start: int, lines: list[str], img_pages: set[int]) -> bool:
    if not img_pages: return False
    page = sum(1 for i in range(start) if i < len(lines) and lines[i] == "\f")
    return page in img_pages


def resolve(entry: dict) -> Path | None:
    fn = entry["filename"]
    for d in [CORPUS_DIR / entry["paper_type"].lower(), CORPUS_DIR]:
        p = d / fn
        if p.exists(): return p
    for d in CORPUS_DIR.iterdir():
        if d.is_dir() and (d / fn).exists(): return d / fn
    return None


def process(qp: dict, ak_entry: dict | None, dry_run: bool = False) -> dict:
    fn = qp["filename"]
    pt, yr, sec = qp["paper_type"], qp["year"], qp["section"]
    log.info("Processing: %s (%s %s)", fn, pt, yr)

    path = resolve(qp)
    if not path:
        return {"file": fn, "error": "not found", "questions": 0}

    text = pdftotext_layout(str(path))
    if not text.strip():
        return {"file": fn, "error": "empty", "questions": 0}

    # Check for scanned PDF
    if is_scanned_pdf(text):
        log.warning("  SCANNED PDF — cannot extract text")
        return {"file": fn, "error": "scanned PDF (needs OCR)", "questions": 0}

    img_pages = get_image_pages(str(path))
    if img_pages:
        log.info("  %d image pages", len(img_pages))

    ak = None
    if ak_entry:
        ak_path = resolve(ak_entry)
        if ak_path:
            ak_text = pdftotext_layout(str(ak_path))
            ak = parse_answer_key(ak_text)
            log.info("  AK: %d answers", len(ak))

    expected = find_expected_count(text, ak, paper_type=pt)
    # TMUA papers always have 20 questions; if count not found, default to 20
    if expected == 0 and pt == "TMUA":
        expected = 20
        log.info("  Expected: %d (TMUA default)", expected)
    else:
        log.info("  Expected: %d", expected)

    qs, errs = parse_questions_layout(text, expected, ak, img_pages, paper_type=pt)
    
    # Fallback: try non-layout mode if layout mode failed
    if len(qs) == 0 and expected > 0:
        log.info("  Layout mode failed, trying non-layout...")
        plain_text = pdftotext_plain(str(path))
        if plain_text.strip():
            qs2, errs2 = parse_questions_layout(plain_text, expected, ak, img_pages, paper_type=pt)
            if len(qs2) > len(qs):
                text = plain_text
                qs, errs = qs2, errs2
                log.info("  Non-layout got %d questions", len(qs))
    
    log.info("  Got: %d", len(qs))
    for e in errs[:5]: log.warning("  %s", e)
    if len(errs) > 5: log.warning("  +%d more", len(errs) - 5)

    stag = sec.upper().replace("SECTION", "S").replace("Paper", "P").replace(" ", "")
    ordered = [{
        "id": f"{pt}-{yr}-{stag}-Q{q['question_number']}",
        "year": yr, "paper": pt, "section": stag,
        "question_number": q["question_number"],
        "question_text": q["question_text"],
        "has_diagram": q["has_diagram"],
        "diagram_images": [],
        "options": q["options"],
        "correct_answer": q["correct_answer"],
        "raw_text": q["raw_text"],
    } for q in qs]

    if not dry_run:
        out = OUTPUT_DIR / f"{pt}_{yr}_{stag}_questions.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"source_file": fn, "paper_type": pt, "year": yr,
                       "section": sec, "total_questions": len(ordered),
                       "questions": ordered}, f, indent=2, ensure_ascii=False)

    return {"file": fn, "expected": expected, "questions": len(ordered),
            "errors": errs, "image_pages": len(img_pages),
            "ak_answers": len(ak) if ak else 0}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper"); ap.add_argument("--year")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.verbose: log.setLevel(logging.DEBUG)

    with open(MANIFEST) as f: manifest = json.load(f)
    qps = [e for e in manifest if e["kind"] == "QuestionPaper"]
    ak_idx = {(e["paper_type"], e["year"], e["section"]): e
              for e in manifest if e["kind"] == "AnswerKey"}
    if args.paper:
        qps = [e for e in qps if e["paper_type"].upper() == args.paper.upper()]
    if args.year:
        qps = [e for e in qps if str(e["year"]) == str(args.year)]
    qps.sort(key=lambda e: ({"ENGAA":0,"NSAA":1,"TMUA":2}.get(e["paper_type"],99),
                             str(e["year"]), e.get("section","")))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    stats = []
    tot_q = tot_err = 0
    for qp in qps:
        s = process(qp, ak_idx.get((qp["paper_type"], qp["year"], qp["section"])),
                    dry_run=args.dry_run)
        stats.append(s)
        tot_q += s.get("questions", 0)
        tot_err += len(s.get("errors", []))

    print(f"\n{'='*60}\nEXTRACTION SUMMARY\n{'='*60}")
    print(f"Papers: {len(stats)} | Questions: {tot_q}")
    missing = [f"{s['file']}: {e}" for s in stats for e in s.get("errors",[]) if "MISSING" in e]
    if missing:
        print(f"\nMissing: {len(missing)}")
        for e in missing[:10]: print(f"  {e}")
        if len(missing)>10: print(f"  +{len(missing)-10} more")
    print(f"\n{'File':<50} {'Exp':>4} {'Got':>4} {'AK':>4}")
    print("-"*65)
    for s in stats:
        if "error" in s:
            print(f"{s['file']:<50} {'ERR':>4} {s['error']}")
        else:
            print(f"{s['file']:<50} {s.get('expected','?'):>4} {s['questions']:>4} "
                  f"{s.get('ak_answers',0):>4}")
    print(f"\nOutput: {OUTPUT_DIR}" if not args.dry_run else "")


if __name__ == "__main__":
    main()
