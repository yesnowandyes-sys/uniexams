#!/usr/bin/env python3
"""
Extract MCQ questions from NSAA Section 2 papers (2020+ format).

NSAA S2 (2020-2022) has 3 parts:
  Part X: Physics (Q1-Q20)
  Part Y: Chemistry (Q21-Q40)
  Part Z: Biology (Q41-Q60)

Each question is MCQ with options A-H (up to 8).
Pre-2020 NSAA S2 papers are written-answer format — NOT processed.

Usage:
    python3 extract_nsaa_s2.py
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:
    print("ERROR: pip install pymupdf"); sys.exit(1)

CORPUS_DIR = Path("/home/ubuntu/.paperclip/esat-shared/corpus/nsaa")
OUTPUT_DIR = Path("/home/ubuntu/.paperclip/esat-shared/corpus/json/nsaa_s2")
IMAGE_DIR  = Path("/home/ubuntu/.paperclip/esat-shared/corpus/images")

MCQ_PAPERS = [
    {"year": 2020, "specimen": False, "qp": "NSAA_2020_S2_QuestionPaper.pdf",
     "ak": "NSAA_2020_S2_AnswerKey.pdf"},
    {"year": 2021, "specimen": False, "qp": "NSAA_2021_S2_QuestionPaper.pdf",
     "ak": "NSAA_2021_S2_AnswerKey.pdf"},
    {"year": 2022, "specimen": False, "qp": "NSAA_2022_S2_QuestionPaper.pdf",
     "ak": "NSAA_2022_S2_AnswerKey.pdf"},
    {"year": 2020, "specimen": True,  "qp": "NSAA_2020_Specimen_S2_QuestionPaper.pdf",
     "ak": "NSAA_2020_Specimen_S2_AnswerKey.pdf"},
]


def pdftotext_layout(pdf_path):
    r = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"],
                       capture_output=True, text=True, timeout=60)
    return r.stdout if r.returncode == 0 else ""


def get_page_of_line(lines_so_far):
    """Count which PDF page (0-indexed) we're on based on form feeds."""
    return sum(1 for l in lines_so_far if "\f" in l)


def extract_images_for_pdf(pdf_path, year, specimen):
    """Extract images from PDF. Returns {page_0indexed: [filenames]}."""
    page_images = {}
    spec_tag = "spec_" if specimen else ""
    try:
        doc = pymupdf.open(str(pdf_path))
        img_counter = 0
        for i, page in enumerate(doc):
            imgs = page.get_images(full=True)
            if not imgs:
                continue
            for img_info in imgs:
                xref = img_info[0]
                try:
                    pix = pymupdf.Pixmap(doc, xref)
                    if pix.n - pix.alpha > 3:
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    if pix.width < 30 or pix.height < 30:
                        pix = None
                        continue
                    img_counter += 1
                    fname = f"NSAA-{year}-S2-{spec_tag}p{i+1}-fig{img_counter}.png"
                    fpath = IMAGE_DIR / fname
                    pix.save(str(fpath))
                    pix = None
                    page_images.setdefault(i, []).append(fname)
                except Exception:
                    pass
        doc.close()
    except Exception as e:
        print(f"  WARNING: Image extraction failed: {e}")
    return page_images


# ---------- Answer Key Parsers ----------

def parse_ak_standard(text):
    """Parse 2021/2022 format: 'Q1  E  PHYS' lines."""
    answers = {}
    for m in re.finditer(r"Q(\d+)\s+([A-H])\s+(?:PHYS|CHEM|BIOL)", text):
        qn = int(m.group(1))
        if 1 <= qn <= 60:
            answers[qn] = m.group(2)
    return answers

def parse_ak_2020_combined(text):
    """Parse 2020 'Sections 1 & 2' AK. S2 is the 'Part 2' section."""
    answers = {}
    # Split at "Part 2" marker
    parts = re.split(r"Part\s*2[a-d]?", text)
    s2_text = parts[-1] if len(parts) > 1 else text
    for m in re.finditer(r"Q(\d+)\s+([A-H])\s+(?:PHYS|CHEM|BIOL)", s2_text):
        qn = int(m.group(1))
        if 1 <= qn <= 60:
            answers[qn] = m.group(2)
    return answers

def parse_ak_specimen_2020(text):
    """Parse specimen 2020 three-column format."""
    answers = {}
    m = re.search(r"Answer Key", text)
    section = text[m.end():] if m else text
    for line in section.split("\n"):
        s = line.strip()
        if not s:
            continue
        # Three pairs: num ans num ans num ans
        m3 = re.match(r"^(\d+)\s+([A-H])\s+(\d+)\s+([A-H])\s+(\d+)\s+([A-H])\s*$", s)
        if m3:
            for q, a in [(int(m3.group(1)), m3.group(2)),
                         (int(m3.group(3)), m3.group(4)),
                         (int(m3.group(5)), m3.group(6))]:
                if 1 <= q <= 30:
                    answers[q] = a
            continue
        m2 = re.match(r"^(\d+)\s+([A-H])\s+(\d+)\s+([A-H])\s*$", s)
        if m2:
            answers[int(m2.group(1))] = m2.group(2)
            answers[int(m2.group(3))] = m2.group(4)
            continue
        m1 = re.match(r"^(\d+)\s+([A-H])\s*$", s)
        if m1:
            answers[int(m1.group(1))] = m1.group(2)
    return answers


def load_answer_key(paper):
    """Load answer key for paper."""
    year, specimen = paper["year"], paper["specimen"]
    
    if year == 2022 and not specimen:
        # Use combined PDF which has S2 AK on last pages
        combined = CORPUS_DIR / "NSAA_2022_Combined.pdf"
        if combined.exists():
            return parse_ak_standard(pdftotext_layout(combined))
    
    ak_path = CORPUS_DIR / paper.get("ak", "")
    if not ak_path.exists():
        return {}
    
    text = pdftotext_layout(ak_path)
    
    if specimen and year == 2020:
        return parse_ak_specimen_2020(text)
    elif year == 2020 and not specimen:
        return parse_ak_2020_combined(text)
    else:
        return parse_ak_standard(text)


# ---------- Question Extraction ----------

# Match a question start line: starts with a number at col 0, followed by 2+ spaces, then text
Q_START_RE = re.compile(r"^(\d{1,2})\s{2,}(\S.*)$")
# Match an option line: single letter A-H at col 0, followed by 2+ spaces, then text
OPT_RE = re.compile(r"^\s{0,8}([A-H])\s{2,}(\S.*)$")
# Match an option line: single letter A-H at col 0, alone
OPT_ALONE_RE = re.compile(r"^\s{0,8}([A-H])\s*$")
# Match part headers
# Section header: at col 0 (no leading spaces). Page headers are indented.
PART_SECTION_RE = re.compile(r"^PART\s+([XYZ])\s+(Physics|Chemistry|Biology)\s*$", re.IGNORECASE)
# Page header: indented version (has leading whitespace)
PART_PAGE_RE = re.compile(r"^\s+PART\s+([XYZ])\s+(PHYSICS|CHEMISTRY|BIOLOGY)\s*$", re.IGNORECASE)
# Lines to skip (noise)
NOISE_RE = re.compile(
    r"^(PART [XYZ]\s+(PHYSICS|CHEMISTRY|BIOLOGY)|"
    r"\d{1,3}|"  # page numbers
    r"©|PV\d|BLANK PAGE|Paper content|Periodic Table|"
    r"This page is intentionally)", re.I)


def find_question_starts(lines, q_min, q_max):
    """Find all lines that start a question.
    
    Returns list of (line_index, question_number) sorted by line_index.
    """
    starts = []
    for i, line in enumerate(lines):
        m = Q_START_RE.match(line)
        if m:
            num = int(m.group(1))
            if q_min <= num <= q_max:
                # Validate: check it's not a number in the periodic table or similar
                # Real questions have text after the number that isn't just more numbers
                text_after = m.group(2).strip()
                if len(text_after) > 3:  # Real question has meaningful text
                    starts.append((i, num))
    return starts


def select_question_sequence(candidates, q_min, q_max):
    """From candidates [(line_idx, q_num), ...], select the correct sequence.
    
    Walk through candidates and pick the first occurrence of each question number
    in order, ensuring each selection comes after the previous one.
    """
    selected = {}  # q_num -> line_idx
    last_line = -1
    
    for target in range(q_min, q_max + 1):
        found = False
        for li, num in candidates:
            if li <= last_line:
                continue
            if num == target:
                selected[target] = li
                last_line = li
                found = True
                break
        if not found:
            pass  # Will be recorded as error
    return selected


def extract_question_text_and_options(block_lines, q_num):
    """From a block of lines for one question, extract text and options.
    
    Skip noise lines (page headers, page numbers, etc.)
    """
    q_parts = []
    options = {}
    in_options = False
    current_opt = None
    
    for line in block_lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Skip noise
        if PART_SECTION_RE.match(line) or PART_PAGE_RE.match(line):
            continue
        if re.match(r"^\d{1,3}$", stripped):  # page number
            continue
        if stripped.startswith("©") or stripped.startswith("PV"):
            continue
        if "BLANK PAGE" in stripped or "intentionally left blank" in stripped.lower():
            continue
        if re.match(r"^Paper content", stripped, re.I):
            continue
        if "Periodic Table" in stripped:
            continue
        
        # Option line?
        m = OPT_RE.match(line)
        if m:
            in_options = True
            current_opt = m.group(1)
            options[current_opt] = m.group(2).strip()
            continue
        
        m = OPT_ALONE_RE.match(line)
        if m:
            in_options = True
            current_opt = m.group(1)
            options.setdefault(current_opt, "")
            continue
        
        # Continuation of option text (indented more than the option letter)
        if in_options and current_opt:
            indent = len(line) - len(line.lstrip())
            if indent >= 6 and not Q_START_RE.match(line) and not PART_SECTION_RE.match(line):
                options[current_opt] += " " + stripped
                continue
            # Not indented — could be end of options
        
        # Question text
        # Remove leading question number if present
        text = re.sub(r"^\s*" + str(q_num) + r"\s{2,}", "", line).strip()
        if text:
            q_parts.append(text)
    
    return "\n".join(q_parts).strip(), options


def process_paper(paper):
    year = paper["year"]
    specimen = paper["specimen"]
    tag = f"NSAA {year}" + (" Specimen" if specimen else "")
    qp_path = CORPUS_DIR / paper["qp"]
    
    print(f"\n{'='*60}")
    print(f"Processing: {tag} S2")
    
    if not qp_path.exists():
        print(f"  ERROR: File not found: {qp_path}")
        return {"year": year, "specimen": specimen, "error": "file not found",
                "questions": [], "total": 0, "errors": [], "images": 0, "ak_count": 0}
    
    # Extract text
    text = pdftotext_layout(qp_path)
    if not text.strip():
        print(f"  ERROR: Empty text extraction")
        return {"year": year, "specimen": specimen, "error": "empty text",
                "questions": [], "total": 0, "errors": [], "images": 0, "ak_count": 0}
    
    lines = text.split("\n")
    
    # Extract images
    print(f"  Extracting images...")
    page_images = extract_images_for_pdf(qp_path, year, specimen)
    total_imgs = sum(len(v) for v in page_images.values())
    print(f"  Extracted {total_imgs} images from {len(page_images)} pages")
    
    # Find part boundaries (section headers at col 0, not page headers)
    part_starts = {}  # part_label -> line_index
    for i, line in enumerate(lines):
        if PART_SECTION_RE.match(line):
            label = line[5].upper()
            if label not in part_starts:  # Take FIRST occurrence (actual section start)
                part_starts[label] = i
    
    print(f"  Part section starts: {part_starts}")
    
    # Determine parts config
    if specimen:
        parts_config = [
            {"label": "X", "subject": "physics",   "q_min": 1,  "q_max": 10},
            {"label": "Y", "subject": "chemistry", "q_min": 11, "q_max": 20},
            {"label": "Z", "subject": "biology",   "q_min": 21, "q_max": 30},
        ]
    else:
        parts_config = [
            {"label": "X", "subject": "physics",   "q_min": 1,  "q_max": 20},
            {"label": "Y", "subject": "chemistry", "q_min": 21, "q_max": 40},
            {"label": "Z", "subject": "biology",   "q_min": 41, "q_max": 60},
        ]
    
    all_questions = []
    all_errors = []
    
    for idx, pc in enumerate(parts_config):
        label = pc["label"]
        start = part_starts.get(label, 0)
        # End is the start of the next part, or end of file
        if idx + 1 < len(parts_config):
            next_label = parts_config[idx + 1]["label"]
            end = part_starts.get(next_label, len(lines))
        else:
            end = len(lines)
        
        # Search for questions within this part
        section_lines = lines[start:end]
        # Adjust line indices to be absolute
        candidates = []
        for i, line in enumerate(section_lines):
            m = Q_START_RE.match(line)
            if m:
                num = int(m.group(1))
                if pc["q_min"] <= num <= pc["q_max"]:
                    text_after = m.group(2).strip()
                    if len(text_after) > 3:
                        candidates.append((i, num))
        
        print(f"  Part {label} ({pc['subject']}): {len(candidates)} candidates for Q{pc['q_min']}-Q{pc['q_max']}")
        
        # Select correct sequence
        selected = select_question_sequence(candidates, pc["q_min"], pc["q_max"])
        
        missing = [q for q in range(pc["q_min"], pc["q_max"] + 1) if q not in selected]
        if missing:
            for mq in missing:
                all_errors.append(f"Q{mq}: MISSING ({pc['subject']})")
            print(f"    Missing: {missing}")
        
        # Extract text and options for each question
        sorted_qs = sorted(selected.keys())
        for qi, q_num in enumerate(sorted_qs):
            q_start_line = selected[q_num]
            q_end_line = selected[sorted_qs[qi + 1]] if qi + 1 < len(sorted_qs) else len(section_lines)
            block = section_lines[q_start_line:q_end_line]
            
            q_text, options = extract_question_text_and_options(block, q_num)
            
            # Determine page for image mapping
            abs_line = start + q_start_line
            page_num = sum(1 for l in lines[:abs_line] if "\f" in l)
            has_diag = page_num in page_images if page_images else False
            diag_imgs = page_images.get(page_num, []) if has_diag else []
            
            all_questions.append({
                "id": f"NSAA-{year}-S2-{f'SPEC-' if specimen else ''}{label}-Q{q_num}",
                "year": year,
                "paper": "NSAA",
                "section": "S2",
                "subject": pc["subject"],
                "part": label,
                "question_number": q_num,
                "question_text": q_text,
                "has_diagram": has_diag,
                "diagram_images": diag_imgs,
                "options": options,
                "correct_answer": None,
            })
        
        print(f"    Extracted {len(sorted_qs)} questions")
    
    # Load and match answer keys
    ak = load_answer_key(paper)
    print(f"  Answer key: {len(ak)} answers")
    matched = 0
    for q in all_questions:
        ans = ak.get(q["question_number"])
        if ans:
            q["correct_answer"] = ans
            matched += 1
    print(f"  Matched {matched}/{len(all_questions)} answers")
    
    # Save per-subject JSON
    for subject in ["physics", "chemistry", "biology"]:
        subject_qs = [q for q in all_questions if q["subject"] == subject]
        if not subject_qs:
            continue
        spec_tag = "specimen_" if specimen else ""
        out_file = OUTPUT_DIR / f"nsaa_{year}_{spec_tag}s2_{subject}.json"
        output = {
            "source_file": paper["qp"],
            "paper": "NSAA",
            "year": year,
            "specimen": specimen,
            "section": "S2",
            "subject": subject,
            "total_questions": len(subject_qs),
            "has_answer_key": bool(ak),
            "questions": subject_qs,
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"  Saved: {out_file.name} ({len(subject_qs)} questions)")
    
    return {
        "year": year,
        "specimen": specimen,
        "questions": all_questions,
        "total": len(all_questions),
        "errors": all_errors,
        "images": total_imgs,
        "ak_count": len(ak),
        "answers_matched": matched,
    }


def verify(all_results):
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")
    
    total_q = sum(r.get("total", 0) for r in all_results)
    all_qs = []
    for r in all_results:
        all_qs.extend(r.get("questions", []))
    
    print(f"Total questions extracted: {total_q}")
    
    issues = []
    
    # Check expected counts
    for r in all_results:
        tag = f"NSAA {r['year']}" + (" Specimen" if r["specimen"] else "")
        expected = 30 if r["specimen"] else 60
        if r.get("total", 0) != expected:
            issues.append(f"{tag}: expected {expected}, got {r.get('total', 0)}")
        if r.get("errors"):
            issues.append(f"{tag}: {len(r['errors'])} errors")
    
    # Check duplicates
    ids = [q["id"] for q in all_qs]
    dups = set(x for x in ids if ids.count(x) > 1)
    if dups:
        issues.append(f"Duplicate IDs: {dups}")
    
    # Answer key coverage
    no_ans = [q for q in all_qs if not q.get("correct_answer")]
    if no_ans:
        print(f"Questions without answer key: {len(no_ans)}")
    
    # Diagrams
    diag_count = sum(1 for q in all_qs if q.get("has_diagram"))
    print(f"Questions with diagrams: {diag_count}")
    
    # Questions with empty text
    empty_text = [q for q in all_qs if not q.get("question_text")]
    if empty_text:
        issues.append(f"{len(empty_text)} questions with empty text: {[q['id'] for q in empty_text[:5]]}")
    
    # Questions with no options
    no_opts = [q for q in all_qs if not q.get("options")]
    if no_opts:
        issues.append(f"{len(no_opts)} questions with no options: {[q['id'] for q in no_opts[:5]]}")
    
    if issues:
        print(f"\nISSUES ({len(issues)}):")
        for i in issues:
            print(f"  - {i}")
    else:
        print("\nAll checks passed ✓")
    
    return issues


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    print("NSAA Section 2 MCQ Extraction")
    print(f"Papers to process: {len(MCQ_PAPERS)}")
    print("Note: Pre-2020 NSAA S2 are written-answer format — skipped")
    
    results = [process_paper(p) for p in MCQ_PAPERS]
    
    issues = verify(results)
    
    # Summary
    print(f"\n{'='*60}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"{'Paper':<30} {'Qs':>5} {'Imgs':>6} {'AK':>5} {'Match':>6} {'Errs':>5}")
    print("-" * 62)
    for r in results:
        tag = f"NSAA {r['year']}" + (" Spec" if r["specimen"] else "") + " S2"
        if "error" in r:
            print(f"{tag:<30} {'ERR':>5}  ({r['error']})")
        else:
            print(f"{tag:<30} {r['total']:>5} {r.get('images',0):>6} "
                  f"{r.get('ak_count',0):>5} {r.get('answers_matched',0):>6} "
                  f"{len(r.get('errors',[])):>5}")
    total_q = sum(r.get("total", 0) for r in results)
    total_errs = sum(len(r.get("errors", [])) for r in results)
    total_imgs = sum(r.get("images", 0) for r in results)
    print("-" * 62)
    print(f"{'TOTAL':<30} {total_q:>5} {total_imgs:>6} {'':>5} {'':>6} {total_errs:>5}")
    print(f"\nOutput: {OUTPUT_DIR}")
    print(f"Images: {IMAGE_DIR}")
    
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
