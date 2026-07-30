#!/usr/bin/env python3
"""
Post-processing script to fix diagram detection in extracted paper JSONs.

Uses pymupdf to detect actual diagrams (figures, graphs, circuit diagrams) vs
mathematical notation (fraction bars, radicals) by analyzing drawing object types.

Key insight: real diagrams contain rectangles and/or curves with fills,
while math notation is composed entirely of lines ('l' items).

Usage:
    python3 fix_diagrams.py [--verbose] [--dry-run]
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:
    os.system(f"{sys.executable} -m pip install pymupdf -q")
    import pymupdf

log = logging.getLogger("fix_diagrams")

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"
JSON_DIR = CORPUS_DIR / "json"
IMAGES_DIR = CORPUS_DIR / "images"

# Diagram detection thresholds
MIN_DIAGRAM_ITEMS = 5
MIN_DIAGRAM_AREA = 800
MIN_DIAGRAM_HEIGHT = 25
EXTRACTION_MARGIN = 12


def is_question_block(text, block_height, question_numbers_set):
    """Check if a text block is a real question start (not a number with units)."""
    m = re.match(r'^(\d{1,2})\s', text) or re.match(r'^(\d{1,2})\.\s', text)
    if not m:
        return None
    num = int(m.group(1))
    if num not in question_numbers_set:
        return None
    rest = text[len(m.group(0)):].strip()
    # Skip tiny blocks that are just numbers with labels
    if block_height < 15:
        return None
    # Skip blocks that look like scientific notation (isotopes, etc.)
    if re.match(r'^\d', rest):  # e.g. "0n" or "235" after the initial number
        return None
    if re.match(r'^°|^(?:cm|mm|km|kg|mol|Pa|Hz|°C|°F|p|n|α|β|γ|e)', rest):
        return None
    # For blocks under 25pts height, require substantial text (real question has a sentence)
    if block_height < 25 and len(rest) < 20:
        return None
    return num


def detect_diagrams_on_page(page, all_question_nums):
    """
    Detect diagrams on a single page and map them to question numbers.
    
    Returns list of (question_number, bbox) tuples for questions that have diagrams.
    """
    blocks = page.get_text("blocks")
    
    # Find question positions
    q_positions = []
    for b in blocks:
        text = b[4].strip()
        qnum = is_question_block(text, b[3] - b[1], all_question_nums)
        if qnum is not None:
            q_positions.append((qnum, b[1]))
    
    if not q_positions:
        return []
    
    q_positions.sort(key=lambda x: x[1])
    
    # Build ranges
    page_height = page.rect.height
    footer_y = page_height - 50
    q_ranges = {}
    for i, (qnum, y_top) in enumerate(q_positions):
        y_end = q_positions[i + 1][1] if i + 1 < len(q_positions) else footer_y
        q_ranges[qnum] = (y_top, y_end)
    
    # Check each question range for diagrams
    results = []
    drawings = page.get_drawings()
    
    # Also check embedded images
    images_info = page.get_image_info()
    
    for qnum, (y_start, y_end) in q_ranges.items():
        # Check embedded images first
        imgs_in_range = []
        for inf in images_info:
            bbox = inf['bbox']
            img_cy = (bbox[1] + bbox[3]) / 2
            if y_start <= img_cy <= y_end:
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if w > 40 and h > 40:
                    imgs_in_range.append(bbox)
        
        if imgs_in_range:
            x0 = min(b[0] for b in imgs_in_range)
            y0 = min(b[1] for b in imgs_in_range)
            x1 = max(b[2] for b in imgs_in_range)
            y1 = max(b[3] for b in imgs_in_range)
            results.append((qnum, (x0, y0, x1, y1)))
            continue
        
        # Check drawings: separate line-only from shape drawings
        pad = 5
        diagram_elements = []
        for d in drawings:
            r = d['rect']
            if r.y1 >= y_start - pad and r.y0 <= y_end + pad:
                items = d.get("items", [])
                for item in items:
                    if item[0] in ('re', 'c', 'qu', 'cs'):
                        diagram_elements.append(r)
                        break
        
        if len(diagram_elements) < MIN_DIAGRAM_ITEMS:
            continue
        
        all_x0 = [r.x0 for r in diagram_elements]
        all_y0 = [r.y0 for r in diagram_elements]
        all_x1 = [r.x1 for r in diagram_elements]
        all_y1 = [r.y1 for r in diagram_elements]
        
        cluster_w = max(all_x1) - min(all_x0)
        cluster_h = max(all_y1) - min(all_y0)
        cluster_area = cluster_w * cluster_h
        
        if cluster_area < MIN_DIAGRAM_AREA or cluster_h < MIN_DIAGRAM_HEIGHT:
            continue
        
        bbox = (min(all_x0), min(all_y0), max(all_x1), max(all_y1))
        results.append((qnum, bbox))
    
    return results


def extract_diagram_image(doc, page_idx, bbox, question_id, fig_num):
    """Extract a diagram region from a page and save as PNG."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    page = doc[page_idx]
    x0, y0, x1, y1 = bbox
    
    x0 = max(0, x0 - EXTRACTION_MARGIN)
    y0 = max(0, y0 - EXTRACTION_MARGIN)
    x1 = min(page.rect.width, x1 + EXTRACTION_MARGIN)
    y1 = min(page.rect.height, y1 + EXTRACTION_MARGIN)
    
    filename = f"{question_id}-fig{fig_num}.png"
    filepath = IMAGES_DIR / filename
    
    mat = pymupdf.Matrix(2, 2)
    clip = pymupdf.Rect(x0, y0, x1, y1)
    pix = page.get_pixmap(matrix=mat, clip=clip)
    pix.save(str(filepath))
    
    return filename


def process_paper(pdf_path, json_path, dry_run=False):
    """Process a single paper: detect diagrams across all pages, then update JSON once."""
    if not pdf_path.exists() or not json_path.exists():
        return None
    
    with open(json_path) as f:
        data = json.load(f)
    
    questions = data.get("questions", [])
    if not questions:
        return None
    
    # Build question number set
    all_question_nums = set(q["question_number"] for q in questions)
    q_by_num = {}
    for q in questions:
        q_by_num.setdefault(q["question_number"], []).append(q)
    
    doc = pymupdf.open(str(pdf_path))
    
    # Phase 1: Scan ALL pages, collect diagram detections per question
    # diagram_detections[qnum] = [(page_idx, bbox), ...]
    diagram_detections = {}
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        detections = detect_diagrams_on_page(page, all_question_nums)
        for qnum, bbox in detections:
            diagram_detections.setdefault(qnum, []).append((page_idx, bbox))
    
    doc.close()
    
    # Phase 2: Apply to questions (each question processed exactly once)
    stats = {"total": len(questions), "with_diagram": 0, "without_diagram": 0, "diagram_ids": []}
    
    for q in questions:
        qnum = q["question_number"]
        dets = diagram_detections.get(qnum, [])
        
        if dets:
            q["has_diagram"] = True
            q["diagram_images"] = []
            stats["with_diagram"] += 1
            stats["diagram_ids"].append(q["id"])
            
            if not dry_run:
                doc = pymupdf.open(str(pdf_path))
                for fig_num, (page_idx, bbox) in enumerate(dets, 1):
                    fname = extract_diagram_image(doc, page_idx, bbox, q["id"], fig_num)
                    q["diagram_images"].append(fname)
                doc.close()
        else:
            q["has_diagram"] = False
            q["diagram_images"] = []
            stats["without_diagram"] += 1
    
    # Save
    if not dry_run:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    return stats


def main():
    ap = argparse.ArgumentParser(description="Fix diagram detection in extracted papers")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(format="%(levelname)s: %(message)s",
                        level=logging.DEBUG if args.verbose else logging.INFO)
    
    # Clear existing diagram images
    if not args.dry_run and IMAGES_DIR.exists():
        for f in IMAGES_DIR.glob("*.png"):
            f.unlink()
    
    all_stats = []
    
    for json_file in sorted(JSON_DIR.rglob("*.json")):
        rel = json_file.relative_to(JSON_DIR)
        parts = rel.parts
        pt = parts[0].upper()
        fn = parts[1]
        
        m = re.match(r'(\d{4}|specimen)_(s\d+|p\d+)\.json', fn)
        if not m:
            continue
        
        year = m.group(1)
        sec_raw = m.group(2)
        
        if pt == "TMUA":
            sec = sec_raw.upper()
            pdf_name = f"TMUA-{year}-paper-{sec[-1]}.pdf"
            pdf_subdir = pt.lower()
            alt_name = f"TMUA-early-{year}-paper-{sec[-1]}.pdf"
        else:
            pdf_name = f"{pt}_{year}_S1_QuestionPaper.pdf"
            pdf_subdir = pt.lower()
            alt_name = None
        
        pdf_path = CORPUS_DIR / pdf_subdir / pdf_name
        if not pdf_path.exists() and alt_name:
            pdf_path = CORPUS_DIR / pdf_subdir / alt_name
        
        if not pdf_path.exists():
            log.warning("PDF not found for %s", fn)
            continue
        
        log.info("Processing %s/%s -> %s", pt, fn, pdf_path.name)
        stats = process_paper(pdf_path, json_file, dry_run=args.dry_run)
        if stats:
            all_stats.append({
                "paper": f"{pt}-{year}-{sec_raw}",
                "total": stats["total"],
                "with_diagram": stats["with_diagram"],
                "without_diagram": stats["without_diagram"],
                "diagram_ids": stats["diagram_ids"],
            })
    
    total_q = sum(s["total"] for s in all_stats)
    total_diag = sum(s["with_diagram"] for s in all_stats)
    pct = total_diag / total_q * 100 if total_q else 0
    
    print(f"\n{'=' * 70}")
    print(f"DIAGRAM DETECTION SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total questions: {total_q}")
    print(f"With diagrams:   {total_diag} ({pct:.1f}%)")
    print(f"Without diagrams: {total_q - total_diag} ({100-pct:.1f}%)")
    print()
    
    print(f"{'Paper':<30} {'Total':>6} {'Diagrams':>9} {'Pct':>6}")
    print("-" * 55)
    for s in all_stats:
        pct_s = s["with_diagram"] / s["total"] * 100 if s["total"] else 0
        print(f"{s['paper']:<30} {s['total']:>6} {s['with_diagram']:>9} {pct_s:>5.1f}%")
    
    print(f"\n--- Sample questions WITH diagrams ---")
    count = 0
    for s in all_stats:
        for qid in s["diagram_ids"]:
            if count >= 15:
                break
            print(f"  {qid}")
            count += 1
        if count >= 15:
            break
    
    print(f"\n--- Sample questions WITHOUT diagrams ---")
    count = 0
    for s in all_stats:
        paper_key = s["paper"]
        pt_l = paper_key.split("-")[0].lower()
        year_sec = "-".join(paper_key.split("-")[1:])
        jpath = JSON_DIR / pt_l / f"{year_sec}.json"
        if jpath.exists():
            with open(jpath) as f:
                d = json.load(f)
            for q in d["questions"]:
                if not q["has_diagram"] and count < 15:
                    print(f"  {q['id']}")
                    count += 1
        if count >= 15:
            break
    
    images = list(IMAGES_DIR.glob("*.png")) if IMAGES_DIR.exists() else []
    print(f"\nExtracted {len(images)} diagram images to {IMAGES_DIR}")


if __name__ == "__main__":
    main()
