#!/usr/bin/env python3
"""
Pass 2 LaTeX converter for ENGAA/NSAA/TMUA corpus.
Converts plain-text math notation to proper LaTeX using regex + GLM-4.7.
Uses urllib for HTTP (requests library has connection issues).
"""

import json, os, re, sys, time, shutil, glob, urllib.request, urllib.error, ssl
from pathlib import Path

API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
API_KEY = "ddbb7b43c8c14cc9a7ba99f101ba08c4.NEN6pitcvh8a2lz8"
MODEL = "glm-4.5-air"  # Faster than glm-4.7 for simple conversion tasks
DELAY = 2.0
TIMEOUT = 90

CORPUS_DIR = Path("/home/ubuntu/.paperclip/esat-shared/corpus/json")
FILES = sorted(
    [f for f in glob.glob(str(CORPUS_DIR / "engaa" / "*.json"))] +
    [f for f in glob.glob(str(CORPUS_DIR / "tmua" / "*.json"))] +
    [f for f in glob.glob(str(CORPUS_DIR / "nsaa" / "*.json")) if "s2" not in f]
)

# Detection patterns
HAS_MATH = re.compile(
    r'\w[\w]*\^|\w_\w|sqrt\(|\d+\.\d*e[+-]?\d+|'
    r'=\s*[\w\d(\\]|<\s*[\w\d(\\]|>\s*[\w\d(\\]|'
    r'\\times|\\frac|\\sqrt|\\text|\\log|\\pm|\\begin|'
    r'\bfrac\b|\bsqrt\b|\b\d+\s*/\s*\d+\b'
)
HAS_LATEX = re.compile(
    r'\\frac|\\sqrt|\\times|\\cdot|\\alpha|\\theta|\\int|\\sum|'
    r'\\pi|\\leq|\\geq|\\neq|\\begin\{|\\text\{|\\pm|\\log_|'
    r'\\partial|\\lambda|\\mu|\\sigma|\\delta|\\omega|\\eta|\\varepsilon'
)
HAS_DOLLAR = re.compile(r'\$[^$\n]+\$', re.MULTILINE)

def needs_latex(text):
    if not text or not text.strip():
        return False
    return bool(HAS_MATH.search(text)) and not (HAS_LATEX.search(text) or HAS_DOLLAR.search(text))

# Regex conversion for simple patterns
def regex_convert(text):
    if not needs_latex(text):
        return text
    if re.search(r'sqrt\([^)]+\)', text) or re.search(r'\w+\^\([^)]+\)', text):
        return None
    if len(text) > 300:
        return None
    
    orig = text
    c = text
    c = re.sub(r'(?<![\/\w\\])(\d+)\/(\d+)(?![\/\w])', r'\\frac{\1}{\2}', c)
    c = re.sub(r'(?<![\/\w\\])([a-zA-Z])\/(\d+)(?![\/\d])', r'\\frac{\1}{\2}', c)
    c = re.sub(r'(\w)\^\(([^)]+)\)', r'\1^{\2}', c)
    c = re.sub(r'(\w)\^(\d{2,})(?!\d)', r'\1^{\2}', c)
    c = re.sub(r'(\w)\^(\d)(?!\d)', r'\1^{\2}', c)
    return c if c != orig else None

# GLM API using urllib
def glm_convert(text):
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": (
                "Convert plain-text math to proper LaTeX notation. "
                "Wrap ALL mathematical expressions in $...$ delimiters. "
                "Keep surrounding prose as plain text outside the delimiters. "
                "Use \\frac{}{}, \\sqrt{}, x^{}, x_{}, \\times, \\leq, \\geq, \\neq, \\pm, etc. "
                "Do NOT change mathematical meaning - only format. "
                "Output ONLY the converted text, no explanations."
            )},
            {"role": "user", "content": text}
        ],
        "temperature": 0.05,
        "max_tokens": 2048,
    }).encode()
    
    req = urllib.request.Request(API_URL, data=payload, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    })
    
    for attempt in range(3):
        try:
            r = urllib.request.urlopen(req, timeout=TIMEOUT)
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"].strip().strip('"')
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            body = e.read().decode()[:200] if e.fp else ""
            print(f"  ⚠️ HTTP {e.code}: {body}", flush=True)
            time.sleep(5)
        except Exception as e:
            print(f"  ⚠️ retry {attempt+1}: {str(e)[:60]}", flush=True)
            time.sleep(8 * (attempt + 1))
    return None

def process_all():
    stats = {"files": 0, "modified": 0, "regex": 0, "glm": 0, "api_calls": 0, "errors": [],
             "examples": []}
    start = time.time()
    
    for fp in FILES:
        stats["files"] += 1
        with open(fp) as f:
            data = json.load(f)
        
        changed = False
        fname = Path(fp).name
        items_this_file = 0
        
        for q in data.get("questions", []):
            qid = q.get("id", "?")
            
            # Question text
            qt = q.get("question_text", "")
            if needs_latex(qt):
                items_this_file += 1
                rc = regex_convert(qt)
                if rc:
                    q["question_text_latex"] = rc
                    stats["regex"] += 1
                    changed = True
                else:
                    print(f"  🔄 {fname} {qid} qt...", end="", flush=True)
                    gc = glm_convert(qt)
                    stats["api_calls"] += 1
                    time.sleep(DELAY)
                    if gc:
                        q["question_text_latex"] = gc
                        stats["glm"] += 1
                        changed = True
                        stats["examples"].append({"f": fname, "q": qid, "type": "qt", "orig": qt[:80], "conv": gc[:80]})
                        print(f" ✅", flush=True)
                    else:
                        stats["errors"].append(f"{fname} {qid} qt")
                        print(f" ❌", flush=True)
            
            # Options
            for key in sorted(q.get("options", {}).keys()):
                val = q["options"][key]
                if needs_latex(val):
                    items_this_file += 1
                    rc = regex_convert(val)
                    if rc:
                        q.setdefault("options_latex", {})[key] = rc
                        stats["regex"] += 1
                        changed = True
                    else:
                        print(f"  🔄 {fname} {qid} opt {key}...", end="", flush=True)
                        gc = glm_convert(val)
                        stats["api_calls"] += 1
                        time.sleep(DELAY)
                        if gc:
                            q.setdefault("options_latex", {})[key] = gc
                            stats["glm"] += 1
                            changed = True
                            stats["examples"].append({"f": fname, "q": qid, "type": f"opt{key}", "orig": val[:80], "conv": gc[:80]})
                            print(f" ✅", flush=True)
                        else:
                            stats["errors"].append(f"{fname} {qid} opt {key}")
                            print(f" ❌", flush=True)
        
        if changed:
            bak = fp + ".bak"
            if not os.path.exists(bak):
                shutil.copy2(fp, bak)
            with open(fp, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            stats["modified"] += 1
            print(f"  💾 {fname} ({items_this_file} items)", flush=True)
    
    elapsed = time.time() - start
    print(f"\n{'═'*50}", flush=True)
    print(f"Done: {elapsed/60:.1f}min | Files: {stats['modified']}/{stats['files']} | Regex: {stats['regex']} | GLM: {stats['glm']} | Calls: {stats['api_calls']} | Errors: {len(stats['errors'])}", flush=True)
    
    # Show some examples
    for ex in stats["examples"][:15]:
        print(f"  {ex['f']} {ex['q']} [{ex['type']}]: {ex['orig'][:60]} → {ex['conv'][:60]}", flush=True)
    
    if stats["errors"]:
        print(f"\nErrors ({len(stats['errors'])}):", flush=True)
        for e in stats["errors"]:
            print(f"  ❌ {e}", flush=True)
    
    return stats

def validate():
    total = 0
    with_latex = 0
    still_plain = 0
    examples = []
    
    for fp in FILES:
        with open(fp) as f:
            data = json.load(f)
        for q in data.get("questions", []):
            total += 1
            qt = q.get("question_text_latex") or q.get("question_text", "")
            opts = {k: q.get("options_latex", {}).get(k, v) for k, v in q.get("options", {}).items()}
            all_text = qt + " " + " ".join(opts.values())
            
            if HAS_MATH.search(all_text):
                if HAS_LATEX.search(all_text) or HAS_DOLLAR.search(all_text):
                    with_latex += 1
                else:
                    still_plain += 1
                    if len(examples) < 30:
                        bad_opts = {k:v[:50] for k,v in opts.items() if HAS_MATH.search(v) and not (HAS_LATEX.search(v) or HAS_DOLLAR.search(v))}
                        examples.append(f"{Path(fp).name} Q{q.get('id','?')}: qt={qt[:80]} opts={bad_opts}")
    
    print(f"\nValidation: {total} total, {with_latex} with LaTeX, {still_plain} still plain", flush=True)
    for e in examples:
        print(f"  ⚠️ {e}", flush=True)
    return still_plain, examples

if __name__ == "__main__":
    stats = process_all()
    remaining, examples = validate()
    
    # Write report
    report = f"""# LaTeX Conversion Report - Pass 2

## Approach
Hybrid: regex for simple patterns (single-char superscripts, simple fractions), GLM-4.5-air for complex cases.
Used urllib instead of requests library due to connection issues.

## Stats
- Regex converted: {stats['regex']}
- GLM converted: {stats['glm']}  
- API calls: {stats['api_calls']}
- Files modified: {stats['modified']}/{stats['files']}
- Errors: {len(stats['errors'])}
- Questions still needing conversion: {remaining}

## Example conversions
"""
    for ex in stats["examples"][:20]:
        report += f"- {ex['f']} {ex['q']} [{ex['type']}]: `{ex['orig']}` → `{ex['conv']}`\n"
    
    if examples:
        report += "\n## Remaining items\n"
        for e in examples:
            report += f"- {e}\n"
    
    if stats["errors"]:
        report += "\n## Errors\n"
        for e in stats["errors"]:
            report += f"- {e}\n"
    
    with open("/home/ubuntu/.paperclip/esat-shared/latex-conversion-report.md", "w") as f:
        f.write(report)
    print(f"\nReport saved to latex-conversion-report.md", flush=True)
    sys.exit(0 if remaining == 0 else 1)
