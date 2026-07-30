#!/usr/bin/env python3
"""
Vision re-extraction pipeline v5: RESUMABLE, processes papers that haven't been done yet.
Detects already-processed papers by comparing current JSON to .bak.
"""

import json, os, sys, time, base64, shutil, traceback, re
from datetime import datetime, timezone
import fitz, requests

API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
API_KEY = "ddbb7b43c8c14cc9a7ba99f101ba08c4.NEN6pitcvh8a2lz8"
MODEL = "glm-4.6v"
DPI = 200
DELAY = 1.5
MAX_RETRIES = 5
BACKOFF = 3

CORPUS = "/home/ubuntu/.paperclip/esat-shared/corpus"
JSON_DIR = os.path.join(CORPUS, "json")
LOG = os.path.join(CORPUS, "vision-re-extraction-log.json")

PROMPT = """Extract ALL questions from this exam page image.

For each question, output a JSON object with:
- "question_number": the question number (integer)  
- "question_text": the full question text with ALL math in LaTeX (use \\frac{}{} for fractions, ^{} for superscripts, \\sqrt{} for roots, \\text{} for units)
- "options": a dict mapping each option letter to its text in LaTeX

Rules:
- Convert ALL math to LaTeX
- Do NOT include question number in question_text  
- Option text is just the answer, NOT prefixed with the letter
- If no questions on this page, output []
- Escape all backslashes properly in JSON strings (use \\ for LaTeX commands)

Output ONLY a valid JSON array. No markdown code fences."""


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
    s, e = text.find("["), text.rfind("]")
    if s >= 0 and e > s:
        c = text[s:e+1]
        for attempt in [c, fix_json_string(c), re.sub(r',\s*([}\]])', r'\1', c), fix_json_string(re.sub(r',\s*([}\]])', r'\1', c))]:
            try: return json.loads(attempt)
            except: pass
    try: return json.loads(fix_json_string(text))
    except: pass
    raise ValueError(f"Cannot parse JSON from {len(text)} chars")


def call_api(img_b64):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
        {"type": "text", "text": PROMPT}
    ]}], "max_tokens": 16384, "temperature": 0}
    for a in range(MAX_RETRIES):
        try:
            r = requests.post(API_URL, headers=headers, json=payload, timeout=180)
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


def is_processed(jp):
    """Check if a paper has already been processed by comparing to .bak"""
    bak = jp + ".bak"
    if not os.path.exists(bak): return False
    try:
        curr = json.load(open(jp))
        orig = json.load(open(bak))
        changed = sum(1 for a, b in zip(curr["questions"], orig["questions"]) 
                      if a.get("question_text") != b.get("question_text"))
        return changed > len(curr["questions"]) * 0.5  # At least 50% changed
    except: return False


def discover():
    papers = []
    for f in sorted(os.listdir(os.path.join(JSON_DIR, "engaa"))):
        if not f.endswith(".json"): continue
        yr = f.replace("_s1.json", "")
        pdf = os.path.join(CORPUS, "engaa", f"ENGAA_{yr}_S1_QuestionPaper.pdf")
        if os.path.exists(pdf):
            papers.append(("engaa", os.path.join(JSON_DIR, "engaa", f), pdf, f"ENGAA {yr} S1"))
    for f in sorted(os.listdir(os.path.join(JSON_DIR, "nsaa"))):
        if not f.endswith(".json") or "s2" in f: continue
        yr = f.replace("_s1.json", "")
        pdf = os.path.join(CORPUS, "nsaa", f"NSAA_{yr}_S1_QuestionPaper.pdf")
        if os.path.exists(pdf):
            papers.append(("nsaa", os.path.join(JSON_DIR, "nsaa", f), pdf, f"NSAA {yr} S1"))
    for f in sorted(os.listdir(os.path.join(JSON_DIR, "tmua"))):
        if not f.endswith(".json"): continue
        base = f.replace(".json", "")
        parts = base.split("_p")
        if len(parts) != 2: continue
        yp, pp = parts
        pn = f"TMUA-early-specimen-paper-{pp}.pdf" if yp == "specimen" else f"TMUA-{yp}-paper-{pp}.pdf"
        pdf = os.path.join(CORPUS, "tmua", pn)
        if os.path.exists(pdf):
            papers.append(("tmua", os.path.join(JSON_DIR, "tmua", f), pdf, f"TMUA {base}"))
    return papers


def process_paper(exam, jp, pp, label, log):
    with open(jp) as f: corpus = json.load(f)
    qs = corpus["questions"]
    bak = jp + ".bak"
    if not os.path.exists(bak): shutil.copy2(jp, bak)
    
    pdf = fitz.open(pp)
    num_pages = len(pdf)
    qnum_idx = {q["question_number"]: i for i, q in enumerate(qs)}
    updated = set()
    pe = ae = 0
    
    for pi in range(num_pages):
        img = pdf[pi].get_pixmap(dpi=DPI).tobytes("png")
        if len(img) < 5000: continue
        img_b64 = base64.standard_b64encode(img).decode()
        sys.stdout.write(f"  p{pi+1}/{num_pages}"); sys.stdout.flush()
        try:
            extracted = call_api(img_b64)
        except ValueError as e:
            sys.stdout.write(" P!"); sys.stdout.flush(); pe += 1; time.sleep(DELAY); continue
        except Exception as e:
            sys.stdout.write(f" E:{str(e)[:20]}"); sys.stdout.flush(); ae += 1; time.sleep(DELAY); continue
        if not isinstance(extracted, list): extracted = [extracted]
        matched = 0
        for eq in extracted:
            qn = eq.get("question_number")
            if qn is None or qn not in qnum_idx or qn in updated: continue
            nt, no = eq.get("question_text", ""), eq.get("options", {})
            if not nt or not no or len(no) < 2: continue
            idx = qnum_idx[qn]
            qs[idx]["question_text"] = nt
            qs[idx]["options"] = no
            updated.add(qn); matched += 1
        sys.stdout.write(f" {'+'+str(matched) if matched else ('['+str(len(extracted))+'f]' if extracted else '-')}\n"); sys.stdout.flush()
        time.sleep(DELAY)
    
    pdf.close()
    missing = sorted(q["question_number"] for q in qs if q["question_number"] not in updated)
    print(f"  => {len(updated)}/{len(qs)} updated, {len(missing)} missing (pe={pe}, ae={ae})", flush=True)
    if missing: print(f"  Missing: {missing[:20]}", flush=True)
    with open(jp, "w") as f: json.dump(corpus, f, indent=2, ensure_ascii=False)
    
    pl = {"label": label, "exam": exam, "total": len(qs), "updated": len(updated),
          "missing": missing, "parse_errors": pe, "api_errors": ae,
          "success": len(missing)==0, "timestamp": datetime.now(timezone.utc).isoformat()}
    log["papers"].append(pl)
    log["total_updated"] += len(updated)
    log["total_missing"] += len(missing)
    # Remove duplicates from log (same label)
    seen = set()
    unique = []
    for p in log["papers"]:
        if p["label"] not in seen:
            seen.add(p["label"]); unique.append(p)
    log["papers"] = unique
    with open(LOG, "w") as f: json.dump(log, f, indent=2)


def main():
    papers = discover()
    # Filter out already-processed
    todo = []
    for exam, jp, pp, label in papers:
        if is_processed(jp):
            print(f"SKIP (already done): {label}", flush=True)
        else:
            todo.append((exam, jp, pp, label))
    
    total_q = sum(len(json.load(open(t[1]))['questions']) for t in todo)
    print(f"\nTo process: {len(todo)}/{len(papers)} papers ({total_q} questions)", flush=True)
    
    # Load existing log
    if os.path.exists(LOG):
        try: log = json.load(open(LOG))
        except: log = {"papers": [], "total_updated": 0, "total_missing": 0}
    else:
        log = {"papers": [], "total_updated": 0, "total_missing": 0}
    
    log["started"] = log.get("started", datetime.now(timezone.utc).isoformat())
    log["model"] = MODEL
    
    for exam, jp, pp, label in todo:
        print(f"\n{'='*60}\n{label} ({len(json.load(open(jp))['questions'])} Qs)\n{'='*60}", flush=True)
        try:
            process_paper(exam, jp, pp, label, log)
        except Exception as e:
            print(f"\nFATAL {label}: {e}", flush=True)
            traceback.print_exc()
            log["papers"].append({"label": label, "success": False, "fatal": str(e)})
            with open(LOG, "w") as f: json.dump(log, f, indent=2)
    
    log["completed"] = datetime.now(timezone.utc).isoformat()
    log["overall_success"] = log["total_missing"] == 0
    with open(LOG, "w") as f: json.dump(log, f, indent=2)
    print(f"\nDONE: {log['total_updated']} updated, {log['total_missing']} missing", flush=True)


if __name__ == "__main__":
    main()
