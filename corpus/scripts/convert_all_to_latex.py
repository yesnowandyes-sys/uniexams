#!/usr/bin/env python3
"""
Comprehensive spoken-text math → LaTeX converter for the entire ESAT question corpus.

Processes ALL JSON files under json/{engaa,nsaa,nsaa_s2,esat,tmua}/ and converts
spoken-text MathML notation in both `options` and `question_text` fields to proper LaTeX.

Uses the GLM-4.7 model via the z.ai API with retry logic and rate limiting.

Existing `options_latex` / `question_text_latex` fields that are already properly
converted are skipped; only fields still containing spoken-text markers are processed.
"""

import json
import os
import re
import sys
import time
import shutil
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' module not found. Install with: pip install requests")
    sys.exit(1)

# ─── Config ───────────────────────────────────────────────────────────────────
API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
API_KEY = "ddbb7b43c8c14cc9a7ba99f101ba08c4.NEN6pitcvh8a2lz8"
MODEL = "glm-4.7"
RATE_LIMIT_DELAY = 3.0   # seconds between API calls
MAX_RETRIES = 5
RETRY_BASE_DELAY = 10    # base seconds for exponential backoff
CORPUS_DIR = Path("/home/ubuntu/.paperclip/esat-shared/corpus")
JSON_DIRS = ["json/engaa", "json/nsaa", "json/nsaa_s2", "json/esat", "json/tmua"]

# ─── Detection ────────────────────────────────────────────────────────────────

# Strong MathML/spoken-text markers — these DEFINITELY need conversion
SPOKEN_RE = re.compile(
    r'\[begin\b|presubscript|presuperscript|rightwards\s+harpoon|'
    r'\bmathsize\b|end\s+style|end\s+root|end\s+fraction|end\s+exponent|'
    r'numerator|denominator|'
    r'to\s+the\s+power\s+of|'
    r'open\s+parentheses|close\s+parentheses|'
    r'straight\s+(?:pi|theta|alpha|beta|gamma|delta|sigma|mu|lambda|omega|'
    r'[a-z]\b(?=\s))|'
    r'plus-or-minus|'
    r'space\s+plus\s+space|space\s+minus\s+space|'
    r'\bsuperscript\b|\bsubscript\b|'
    r'square\s+root\s+of|'
    r'over\s+denominator|'
    r'log\s+subscript|'
    r'\[\s*blank\b|\[\s*space\b|'
    r'equals\s+plus-or-minus|'
    r'\bbegin\s+(?:mathsize|inline)',
    re.IGNORECASE
)

# For question_text, also detect inline bracket notation
BRACKET_MATH_RE = re.compile(
    r'\[[^\]]*(?:style|mathsize|presubscript|presuperscript|straight|'
    r'harpoon|numerator|denominator|fraction|root|superscript|subscript|'
    r'parentheses|plus-or-minus|power|degree|space\s+(?:plus|minus|equals))',
    re.IGNORECASE
)


def field_needs_conversion(text: str) -> bool:
    """Check if a text field contains spoken-text math markers."""
    if not text or not text.strip():
        return False
    return bool(SPOKEN_RE.search(text) or BRACKET_MATH_RE.search(text))


def option_needs_conversion(original: str, latex_version: str) -> bool:
    """Check if an option still needs conversion.
    
    An option needs conversion if:
    - The original has spoken-text markers, AND
    - The latex version is missing, identical to original, or still has spoken markers
    """
    if not field_needs_conversion(original):
        return False
    if not latex_version:
        return True
    if latex_version == original:
        return True
    if field_needs_conversion(latex_version):
        return True
    return False


# ─── API ──────────────────────────────────────────────────────────────────────

OPTIONS_SYSTEM_PROMPT = """\
You are a precise mathematical notation converter. Convert spoken-text MathML descriptions into clean, standard LaTeX.

Rules:
1. Output a JSON object mapping option letters to their LaTeX strings.
2. Use standard LaTeX: \\frac{a}{b} for fractions, \\sqrt{x} for roots, ^{n} for superscripts, _{n} for subscripts.
3. Do NOT wrap output in $ or \\[ \\] delimiters. Output raw LaTeX only.
4. Chemistry isotopes: presuperscript = mass number (top), presubscript = atomic number (bottom). Example: {}^{35}_{17}\\text{Cl}
5. Chemical equilibrium arrows: use \\rightleftharpoons
6. "straight X" means the chemical element/symbol X. "straight pi" = \\pi, "straight theta" = \\theta, etc.
7. "open parentheses" = (, "close parentheses" = )
8. "plus-or-minus" = \\pm
9. "space" between terms usually means multiplication or separation.
10. "to the power of N" = ^{N}
11. "log subscript 10" = \\log_{10}, "log subscript 2" = \\log_{2}
12. "degree" = ^{\\circ}
13. "end style", "end root", "end fraction", "end exponent" are closing markers — ignore them.
14. "blank" before presubscript/presuperscript means it's a bare isotope notation — output just {}^{mass}_{atomic}\\text{Symbol}
15. Units (cm, m/s, kg, J, etc.) should remain as plain text appended to the LaTeX.
16. If an option is already plain text with no math, return it unchanged.
17. Output ONLY the JSON object, no other text or explanation.

Examples:
Input: {"A": "[blank presubscript 17 presuperscript 35] Cl¯"}
Output: {"A": "{}^{35}_{17}\\text{Cl}^-"}

Input: {"A": "[begin mathsize 16px style 1 fourth end style]"}
Output: {"A": "\\frac{1}{4}"}

Input: {"A": "3 to the power of 9"}
Output: {"A": "3^{9}"}

Input: {"A": "[log subscript 10 100]"}
Output: {"A": "\\log_{10}100"}
"""

QTEXT_SYSTEM_PROMPT = """\
You are a precise mathematical notation converter. Convert spoken-text MathML in question text to LaTeX.

Rules:
1. Wrap ONLY the math portions in $...$ inline math delimiters.
2. Keep surrounding English text as plain prose.
3. Use standard LaTeX: \\frac{a}{b}, \\sqrt{x}, ^{n}, _{n}.
4. "straight pi" = \\pi, "straight theta" = \\theta, etc.
5. "open parentheses" = (, "close parentheses" = )
6. "plus-or-minus" = \\pm
7. "to the power of N" = ^{N}
8. "square root of X" = \\sqrt{X}
9. "numerator X over denominator Y" = \\frac{X}{Y}
10. "subscript" = _, "superscript" = ^
11. "degree" or "degrees" = ^{\\circ}
12. Do NOT convert regular English like "a fraction of" or "one third of the way" — only convert actual MathML notation.
13. If the text has no MathML markers, return it unchanged.
14. Output ONLY the converted text, no explanations.

Example:
Input: "What is [begin mathsize 16px style 1 half end style] of the total?"
Output: "What is $\\frac{1}{2}$ of the total?"

Input: "Find [square root of begin inline style 3 over 2 end style end root]"
Output: "Find $\\sqrt{\\frac{3}{2}}$"
"""


def call_api(system_prompt: str, user_prompt: str, max_retries: int = MAX_RETRIES) -> str:
    """Call the GLM-4.7 API with retry logic."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
            
            # Handle rate limiting
            if resp.status_code == 429:
                wait = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"  ⏳ Rate limited (attempt {attempt+1}/{max_retries}), waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            
            # Handle auth errors definitively
            if resp.status_code == 401 or resp.status_code == 403:
                raise Exception(f"Auth error ({resp.status_code}): {resp.text[:200]}")
            
            resp.raise_for_status()
            data = resp.json()
            
            if "error" in data:
                raise Exception(f"API error: {data['error']}")
            
            return data["choices"][0]["message"]["content"]
            
        except requests.exceptions.Timeout:
            wait = RETRY_BASE_DELAY * (attempt + 1)
            print(f"  ⏳ Timeout (attempt {attempt+1}/{max_retries}), waiting {wait}s...", flush=True)
            time.sleep(wait)
        except requests.exceptions.ConnectionError as e:
            wait = RETRY_BASE_DELAY * (attempt + 1)
            print(f"  ⏳ Connection error (attempt {attempt+1}/{max_retries}): {e}, waiting {wait}s...", flush=True)
            time.sleep(wait)
        except Exception as e:
            if "Auth error" in str(e):
                raise
            wait = RETRY_BASE_DELAY * (attempt + 1)
            print(f"  ⚠️ Error (attempt {attempt+1}/{max_retries}): {str(e)[:150]}", flush=True)
            time.sleep(wait)
    
    raise Exception(f"All {max_retries} retries exhausted")


def parse_json_response(text: str) -> dict:
    """Extract JSON object from model response, handling markdown code blocks."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"\s*```", "", cleaned)
    first_brace = cleaned.find('{')
    last_brace = cleaned.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace:last_brace + 1]
    return json.loads(cleaned)


def clean_latex_response(text: str) -> str:
    """Clean up a LaTeX response from the model."""
    cleaned = text.strip()
    # Remove markdown code blocks
    cleaned = re.sub(r"^```[a-z]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    # Remove surrounding quotes
    cleaned = cleaned.strip().strip('"').strip("'")
    return cleaned


# ─── Conversion Logic ─────────────────────────────────────────────────────────

def convert_options(question: dict) -> dict:
    """Convert all options of a question that need it. Returns {letter: latex}."""
    options = question.get("options", {})
    options_latex = dict(question.get("options_latex", {}))
    
    to_convert = {}
    for key in sorted(options.keys()):
        orig = options[key]
        current_latex = options_latex.get(key, "")
        if option_needs_conversion(orig, current_latex):
            to_convert[key] = orig
    
    if not to_convert:
        return {}
    
    # Build prompt
    qtext = question.get("question_text", "")[:300]
    prompt_parts = [
        f"Question context: {qtext}",
        "",
        "Convert these options from spoken-text MathML to LaTeX:",
    ]
    for key in sorted(to_convert.keys()):
        prompt_parts.append(f'"{key}": "{to_convert[key]}"')
    prompt_parts.append("")
    prompt_parts.append('Respond with ONLY a JSON object like: {"A": "\\\\frac{1}{2}", "B": "3^{2}"}')
    
    response = call_api(OPTIONS_SYSTEM_PROMPT, "\n".join(prompt_parts))
    
    try:
        result = parse_json_response(response)
        # Only keep keys we asked for
        return {k: v for k, v in result.items() if k in to_convert}
    except (json.JSONDecodeError, Exception) as e:
        print(f"  ❌ JSON parse error: {e}", flush=True)
        print(f"  Raw response (first 300 chars): {response[:300]}", flush=True)
        return {}


def convert_question_text(question: dict, module: str = "") -> str:
    """Convert question_text field if it needs conversion. Returns LaTeX version or empty string."""
    qt = question.get("question_text", "")
    qt_latex = question.get("question_text_latex", "")
    
    if not field_needs_conversion(qt):
        return ""
    if qt_latex and qt_latex != qt and not field_needs_conversion(qt_latex):
        return ""
    
    prompt = (
        f"Module/subject: {module}\n\n"
        f"Convert the MathML/spoken-text notation in this question text to LaTeX:\n\n"
        f"{qt}\n\n"
        f"Output ONLY the converted text. Wrap math parts in $...$ and keep prose as plain text."
    )
    
    response = call_api(QTEXT_SYSTEM_PROMPT, prompt)
    return clean_latex_response(response)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    stats = {
        "files_scanned": 0,
        "files_modified": 0,
        "questions_scanned": 0,
        "options_converted": 0,
        "question_texts_converted": 0,
        "api_calls": 0,
        "errors": [],
        "examples": [],
    }
    
    start_time = time.time()
    
    for dirname in JSON_DIRS:
        dir_path = CORPUS_DIR / dirname
        if not dir_path.exists():
            continue
        
        for json_file in sorted(dir_path.glob("*.json")):
            stats["files_scanned"] += 1
            file_modified = False
            backup_made = False
            
            print(f"\n{'─' * 60}", flush=True)
            print(f"📂 {json_file.relative_to(CORPUS_DIR)}", flush=True)
            print(f"{'─' * 60}", flush=True)
            
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            questions = data.get("questions", [])
            stats["questions_scanned"] += len(questions)
            
            for i, q in enumerate(questions):
                qid = q.get("id", f"Q{i+1}")
                
                # ── Options ──
                options = q.get("options", {})
                options_latex = dict(q.get("options_latex", {}))
                
                # Detect which options need conversion
                needs = {k: v for k, v in options.items()
                         if option_needs_conversion(v, options_latex.get(k, ""))}
                
                if needs:
                    print(f"  🔧 {qid} options ({len(needs)} to convert)...", end="", flush=True)
                    
                    try:
                        result = convert_options(q)
                        stats["api_calls"] += 1
                        
                        converted = 0
                        for key in sorted(needs.keys()):
                            if key in result:
                                old_val = options[key]
                                new_val = result[key]
                                options_latex[key] = new_val
                                converted += 1
                                stats["options_converted"] += 1
                                
                                if len(stats["examples"]) < 10:
                                    stats["examples"].append({
                                        "file": str(json_file.relative_to(CORPUS_DIR)),
                                        "question": qid,
                                        "option": key,
                                        "original": old_val[:80],
                                        "latex": new_val[:80],
                                    })
                        
                        print(f" ✅ {converted}/{len(needs)} converted", flush=True)
                        
                        if not backup_made:
                            backup_path = json_file.with_suffix(".json.bak")
                            shutil.copy2(json_file, backup_path)
                            backup_made = True
                            file_modified = True
                        
                        q["options_latex"] = options_latex
                        time.sleep(RATE_LIMIT_DELAY)
                        
                    except Exception as e:
                        stats["errors"].append(f"{json_file.name} {qid} options: {str(e)[:120]}")
                        print(f" ❌ ERROR: {str(e)[:100]}", flush=True)
                        # Still save what we have
                        q["options_latex"] = options_latex
                        time.sleep(RATE_LIMIT_DELAY)
                else:
                    # Ensure options_latex exists even if no conversion needed
                    if "options_latex" not in q:
                        q["options_latex"] = dict(options)
                
                # ── Question text ──
                qt = q.get("question_text", "")
                qt_latex_existing = q.get("question_text_latex", "")
                
                if field_needs_conversion(qt):
                    if not qt_latex_existing or qt_latex_existing == qt or field_needs_conversion(qt_latex_existing):
                        print(f"  🔧 {qid} question_text...", end="", flush=True)
                        
                        try:
                            qt_latex = convert_question_text(q, data.get("module", data.get("source_file", "")))
                            stats["api_calls"] += 1
                            
                            if qt_latex:
                                q["question_text_latex"] = qt_latex
                                stats["question_texts_converted"] += 1
                                print(f" ✅ done", flush=True)
                                
                                if not backup_made:
                                    backup_path = json_file.with_suffix(".json.bak")
                                    shutil.copy2(json_file, backup_path)
                                    backup_made = True
                                    file_modified = True
                            else:
                                print(f" ⚠️ empty response", flush=True)
                            
                            time.sleep(RATE_LIMIT_DELAY)
                            
                        except Exception as e:
                            stats["errors"].append(f"{json_file.name} {qid} qtext: {str(e)[:120]}")
                            print(f" ❌ ERROR: {str(e)[:100]}", flush=True)
                            time.sleep(RATE_LIMIT_DELAY)
            
            # Write file if modified
            if file_modified:
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                stats["files_modified"] += 1
                print(f"  💾 Saved {json_file.name}", flush=True)
    
    elapsed = time.time() - start_time
    
    # ── Summary ──
    print(f"\n{'═' * 60}", flush=True)
    print("CONVERSION COMPLETE", flush=True)
    print(f"{'═' * 60}", flush=True)
    print(f"Elapsed time:         {elapsed:.1f}s ({elapsed/60:.1f} min)", flush=True)
    print(f"Files scanned:        {stats['files_scanned']}", flush=True)
    print(f"Files modified:       {stats['files_modified']}", flush=True)
    print(f"Questions scanned:    {stats['questions_scanned']}", flush=True)
    print(f"Options converted:    {stats['options_converted']}", flush=True)
    print(f"Question texts done:  {stats['question_texts_converted']}", flush=True)
    print(f"Total API calls:      {stats['api_calls']}", flush=True)
    print(f"Errors:               {len(stats['errors'])}", flush=True)
    
    if stats["errors"]:
        print(f"\nErrors:", flush=True)
        for err in stats["errors"]:
            print(f"  • {err}", flush=True)
    
    if stats["examples"]:
        print(f"\nExample conversions:", flush=True)
        for ex in stats["examples"][:10]:
            print(f"\n  {ex['file']} → {ex['question']} option {ex['option']}:", flush=True)
            print(f"    BEFORE: {ex['original']}", flush=True)
            print(f"    AFTER:  {ex['latex']}", flush=True)
    
    return stats


if __name__ == "__main__":
    main()
