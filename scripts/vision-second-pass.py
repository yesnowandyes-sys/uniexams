#!/usr/bin/env python3
"""Second pass: targeted extraction of specific missing questions."""

import json, os, sys, time, base64, traceback, re
from datetime import datetime, timezone
import fitz, requests

API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
API_KEY = "ddbb7b43c8c14cc9a7ba99f101ba08c4.NEN6pitcvh8a2lz8"
MODEL = "glm-4.6v"
DPI = 200
DELAY = 2.0
MAX_RETRIES = 3
BACKOFF = 5

CORPUS = "/home/ubuntu/.paperclip/esat-shared/corpus"
JSON_DIR = os.path.join(CORPUS, "json")
LOG = os.path.join(CORPUS, "vision-re-extraction-log.json")

LATEX_CHECK = re.compile(r'\\frac|\\sqrt|\^{|\\times|\\sin|\\cos|\\tan|\\int|\\sum|\\log|\\text\{|\\alpha|\\beta|\\theta|\\lambda|\\mu|\\pi|\\rho|\\omega|\\Delta|\\nabla|\\infty|\\cdot')

TARGETED_PROMPT = """This page contains question number {qn} from a Cambridge admissions test. Extract ONLY question {qn} in LaTeX.

Output a single JSON object with:
- "question_number": {qn}
- "question_text": full question text with ALL math in LaTeX
- "options": dict mapping option letters (A,B,C,D) to their text in LaTeX

Rules:
- Convert ALL math to LaTeX (fractions, superscripts, roots, Greek letters, units)
- Do NOT include question number in question_text
- Escape backslashes properly in JSON
- Output ONLY valid JSON, no markdown fences"""

def fix_json_string(s):
    result = []
    i = 0
    in_string = False
    while i < len(s):
        if not in_string:
            result.append(s[i])
            if s[i] == '"': in_string = True
        else:
            if s[i] == '"' and (i == 0 or s[i-1] != '\\'):
                in_string = False
                result.append(s[i])
            elif s[i] == '\\' and i + 1 < len(s):
                nxt = s[i+1]
                if nxt in '"\\/bfnrtu':
                    result.append(s[i]); result.append(nxt); i += 2; continue
                else:
                    result.append('\\\\'); i += 1; continue
            else:
                result.append(s[i])
        i += 1
    return ''.join(result)


def parse_json(text):
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) >= 3 else (parts[0] if parts[0].strip().startswith("[") else parts[1])
        text = text.strip()
    if text.lower().startswith("json"): text = text[4:].strip()
    # Try object or array
    for opener, closer in [("{", "}"), ("[", "]")]:
        s, e = text.find(opener), text.rfind(closer)
        if s >= 0 and e > s:
            c = text[s:e+1]
            for attempt in [c, fix_json_string(c), re.sub(r',\s*([}\]])', r'\1', c), fix_json_string(re.sub(r',\s*([}\]])', r'\1', c))]:
                try: return json.loads(attempt)
                except: pass
    try: return json.loads(fix_json_string(text))
    except: pass
    raise ValueError(f"Cannot parse JSON from {len(text)} chars")


def call_api(img_b64, qn):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    prompt = TARGETED_PROMPT.format(qn=qn)
    payload = {"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
        {"type": "text", "text": prompt}
    ]}], "max_tokens": 4096, "temperature": 0}
    for a in range(MAX_RETRIES):
        try:
            r = requests.post(API_URL, headers=headers, json=payload, timeout=120)
            if r.status_code == 429: time.sleep(BACKOFF * (2**a) + 1); continue
            if r.status_code >= 500: time.sleep(BACKOFF * (2**a) + 1); continue
            r.raise_for_status()
            return parse_json(r.json()["choices"][0]["message"]["content"])
        except ValueError:
            if a < MAX_RETRIES - 1: time.sleep(BACKOFF * (2**a) + 1)
            else: raise
        except requests.exceptions.Timeout:
            time.sleep(BACKOFF * (2**a) + 1)
        except:
            if a < MAX_RETRIES - 1: time.sleep(BACKOFF * (2**a) + 1)
            else: raise
    raise RuntimeError("Max retries")


def find_pdf_path(exam, label):
    if exam == "engaa":
        yr = label.replace("ENGAA ", "").replace(" S1", "")
        return os.path.join(CORPUS, "engaa", f"ENGAA_{yr}_S1_QuestionPaper.pdf")
    elif exam == "nsaa":
        yr = label.replace("NSAA ", "").replace(" S1", "")
        return os.path.join(CORPUS, "nsaa", f"NSAA_{yr}_S1_QuestionPaper.pdf")
    elif exam == "tmua":
        base = label.replace("TMUA ", "")
        parts = base.split("_p")
        yp, pp = parts
        pn = f"TMUA-early-specimen-paper-{pp}.pdf" if yp == "specimen" else f"TMUA-{yp}-paper-{pp}.pdf"
        return os.path.join(CORPUS, "tmua", pn)
    return None


def find_json_path(exam, label):
    if exam == "engaa":
        yr = label.replace("ENGAA ", "").replace(" S1", "")
        return os.path.join(JSON_DIR, "engaa", f"{yr}_s1.json")
    elif exam == "nsaa":
        yr = label.replace("NSAA ", "").replace(" S1", "")
        return os.path.join(JSON_DIR, "nsaa", f"{yr}_s1.json")
    elif exam == "tmua":
        base = label.replace("TMUA ", "")
        return os.path.join(JSON_DIR, "tmua", f"{base}.json")
    return None


def find_question_page(pdf_path, qn, label):
    """Find which PDF page likely contains question qn by searching for the question number."""
    pdf = fitz.open(pdf_path)
    # Strategy: look for pages that mention the question number
    candidates = []
    for pi in range(len(pdf)):
        text = pdf[pi].get_text()
        # Look for the question number as a standalone number
        patterns = [rf'\b{qn}\b', rf'Question\s*{qn}', rf'Q\s*{qn}']
        for pat in patterns:
            if re.search(pat, text):
                candidates.append(pi)
                break
    pdf.close()
    return candidates


def main():
    log = json.load(open(LOG))
    
    # Collect questions that need re-extraction (no LaTeX)
    to_reextract = []
    for p in log["papers"]:
        missing = p.get("missing", [])
        if not missing:
            continue
        
        exam, label = p["exam"], p["label"]
        jp = find_json_path(exam, label)
        pp = find_pdf_path(exam, label)
        if not jp or not pp or not os.path.exists(jp) or not os.path.exists(pp):
            print(f"SKIP (missing files): {label}")
            continue
        
        corpus = json.load(open(jp))
        qnum_idx = {q["question_number"]: i for i, q in enumerate(corpus["questions"])}
        
        for qn in missing:
            if qn not in qnum_idx:
                continue
            q = corpus["questions"][qnum_idx[qn]]
            qt = q.get("question_text", "")
            opts = q.get("options", {})
            
            # Check if it already has LaTeX
            has_qt_latex = bool(LATEX_CHECK.search(qt))
            has_opt_latex = any(LATEX_CHECK.search(str(v)) for v in opts.values())
            
            if has_qt_latex and has_opt_latex:
                print(f"  SKIP {label} Q{qn}: already has LaTeX")
                continue
            
            to_reextract.append((exam, label, jp, pp, qn))
    
    print(f"\n{'='*60}")
    print(f"Second pass: {len(to_reextract)} questions to re-extract")
    print(f"{'='*60}\n")
    
    if not to_reextract:
        print("Nothing to do!")
        return
    
    fixed = 0
    failed = []
    
    for exam, label, jp, pp, qn in to_reextract:
        print(f"\n{label} Q{qn}...", end=" ", flush=True)
        
        # Find candidate pages
        pages = find_question_page(pp, qn, label)
        if not pages:
            print("NO PAGE FOUND")
            failed.append((label, qn, "no page found"))
            continue
        
        # Try each candidate page
        success = False
        for pi in pages:
            pdf = fitz.open(pp)
            img = pdf[pi].get_pixmap(dpi=DPI).tobytes("png")
            pdf.close()
            if len(img) < 5000:
                continue
            img_b64 = base64.standard_b64encode(img).decode()
            
            try:
                result = call_api(img_b64, qn)
            except Exception as e:
                print(f"API error (p{pi}): {str(e)[:40]}", flush=True)
                continue
            
            # Handle both object and array results
            if isinstance(result, list):
                items = result
            else:
                items = [result]
            
            for item in items:
                rn = item.get("question_number")
                if rn != qn:
                    continue
                nt = item.get("question_text", "")
                no = item.get("options", {})
                if nt and no and len(no) >= 2:
                    # Update the corpus
                    corpus = json.load(open(jp))
                    qnum_idx2 = {q["question_number"]: i for i, q in enumerate(corpus["questions"])}
                    idx = qnum_idx2[qn]
                    corpus["questions"][idx]["question_text"] = nt
                    corpus["questions"][idx]["options"] = no
                    with open(jp, "w") as f:
                        json.dump(corpus, f, indent=2, ensure_ascii=False)
                    print(f"FIXED (p{pi+1})")
                    fixed += 1
                    success = True
                    break
            
            if success:
                break
            time.sleep(DELAY)
        
        if not success:
            print(f"FAILED (tried {len(pages)} pages)")
            failed.append((label, qn, f"tried pages {pages}"))
        
        time.sleep(DELAY)
    
    print(f"\n{'='*60}")
    print(f"Second pass complete: {fixed}/{len(to_reextract)} fixed")
    if failed:
        print(f"Still failed: {len(failed)}")
        for label, qn, reason in failed:
            print(f"  {label} Q{qn}: {reason}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
