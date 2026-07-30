#!/usr/bin/env python3
"""
Convert ESAT specimen question options from spoken-text format to LaTeX
using the GLM-4.7 model via the z.ai API.
"""

import json
import os
import re
import time
import sys
import requests
from pathlib import Path

# --- Config ---
API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
API_KEY = "ddbb7b43c8c14cc9a7ba99f101ba08c4.NEN6pitcvh8a2lz8"
MODEL = "glm-4.7"
RATE_LIMIT_DELAY = 3.0  # seconds between API calls
MAX_RETRIES = 5
RETRY_DELAY = 10  # base seconds for retries

BASE_DIR = Path("/home/ubuntu/.paperclip/esat-shared/corpus/json/esat")
FILES = [
    "esat_specimen_biology.json",
    "esat_specimen_chemistry.json",
    "esat_specimen_maths1.json",
    "esat_specimen_maths2.json",
    "esat_specimen_physics.json",
]


def needs_conversion(text: str) -> bool:
    """Check if text contains spoken-text math markers."""
    if not text or not text.strip():
        return False
    stripped = text.strip()
    if not stripped.startswith("["):
        return False
    math_keywords = [
        "begin", "end", "fraction", "numerator", "denominator",
        "square root", "end root", "over", "superscript", "presubscript",
        "presuperscript", "straight", "pi", "theta", "alpha",
        "beta", "gamma", "delta", "sigma", "mu", "lambda", "omega",
        "plus", "minus", "times", "divided", "squared", "cubed",
        "end style", "mathsize",
    ]
    lower = stripped.lower()
    return any(kw in lower for kw in math_keywords)


def call_api(prompt: str, max_retries: int = MAX_RETRIES) -> str:
    """Call API with retry logic."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise mathematical notation converter. "
                    "Convert spoken-text descriptions of mathematical expressions into clean, standard LaTeX.\n\n"
                    "Rules:\n"
                    "1. Output a JSON object where keys are option letters and values are LaTeX strings.\n"
                    "2. Use standard LaTeX math notation (fractions, radicals, superscripts, etc.).\n"
                    "3. Do NOT wrap in $ or \\[ \\]. Just the raw LaTeX.\n"
                    "4. Maintain mathematical accuracy.\n"
                    "5. 'straight pi' means the Greek letter π (\\pi).\n"
                    "6. 'presubscript X presuperscript Y' means ^{Y}_{X} (e.g., {}^{35}_{17} for an isotope).\n"
                    "7. 'blank' in isotope notation means the symbol placeholder — output just the superscript/subscript part.\n"
                    "8. 'space' between tokens typically means multiplication.\n"
                    "9. If an option is plain text (no math), output it as-is.\n"
                    "10. Output ONLY the JSON object, no other text.\n"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
            if resp.status_code == 429 or (resp.status_code == 200 and resp.text.strip().startswith('{"error"')):
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"  Rate limited (attempt {attempt+1}), waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise Exception(f"API error: {data['error']}")
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            wait = RETRY_DELAY * (attempt + 1)
            print(f"  Timeout (attempt {attempt+1}), waiting {wait}s...", flush=True)
            time.sleep(wait)
        except Exception as e:
            wait = RETRY_DELAY * (attempt + 1)
            print(f"  Error (attempt {attempt+1}): {e}", flush=True)
            time.sleep(wait)
    raise Exception("All retries exhausted")


def parse_json_response(text: str) -> dict:
    """Extract JSON from model response, handling markdown code blocks."""
    # Remove markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"\s*```", "", cleaned)
    # Find the JSON object (from first { to last })
    first_brace = cleaned.find('{')
    last_brace = cleaned.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace:last_brace + 1]
    return json.loads(cleaned)


def convert_question_options(question_text: str, options: dict) -> dict:
    """Send all options of a question to the API in one batch. Returns dict of key -> LaTeX."""
    to_convert = {k: v for k, v in options.items() if needs_conversion(v)}
    if not to_convert:
        return {}

    prompt_lines = [
        f"Question context: {question_text[:500]}",
        "",
        "Convert these options from spoken-text to LaTeX:",
    ]
    for key in sorted(to_convert.keys()):
        prompt_lines.append(f'"{key}": "{to_convert[key]}"')
    prompt_lines.append("")
    prompt_lines.append("Respond with ONLY a JSON object like: {\"A\": \"\\\\frac{1}{2}\", \"B\": \"3\"}")

    response = call_api("\n".join(prompt_lines))

    try:
        result = parse_json_response(response)
        # Filter to only requested keys
        return {k: v for k, v in result.items() if k in to_convert}
    except (json.JSONDecodeError, Exception) as e:
        print(f"  Parse error: {e}", flush=True)
        print(f"  Raw response: {response[:200]}", flush=True)
        return {}


def convert_text_field(text: str, context: str = "") -> str:
    """Convert a single text field to LaTeX."""
    if not needs_conversion(text):
        return ""
    prompt = (
        f"Context: {context[:300]}\n\n"
        f"Convert this spoken-text math to LaTeX:\n{text}\n\n"
        f"Respond with ONLY the LaTeX, nothing else."
    )
    response = call_api(prompt)
    # Clean: remove $ signs, code blocks, quotes
    cleaned = response.strip().strip("$").strip()
    cleaned = re.sub(r"^```[a-z]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned


def main():
    stats = {
        "files_processed": 0,
        "questions_total": 0,
        "questions_with_math": 0,
        "options_converted": 0,
        "question_text_converted": 0,
        "errors": [],
        "examples": [],
    }

    for fname in FILES:
        fpath = BASE_DIR / fname
        if not fpath.exists():
            print(f"File not found: {fpath}")
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {fname}")
        print(f"{'='*60}")

        with open(fpath, "r") as f:
            data = json.load(f)

        questions = data.get("questions", [])
        stats["questions_total"] += len(questions)

        for i, q in enumerate(questions):
            qnum = q.get("question_number", i + 1)

            # --- Convert options ---
            options = q.get("options", {})
            has_math = any(needs_conversion(v) for v in options.values())

            if has_math:
                stats["questions_with_math"] += 1
                print(f"  Q{qnum} [math options] ", end="", flush=True)

                try:
                    result = convert_question_options(q.get("question_text", ""), options)
                    options_latex = dict(options)  # Start with originals
                    options_latex.update(result)

                    converted_count = sum(1 for k in to_c if k in result) if (to_c := {k: v for k, v in options.items() if needs_conversion(v)}) else 0
                    stats["options_converted"] += len(to_c)

                    if result and len(stats["examples"]) < 5:
                        first_key = sorted(result.keys())[0]
                        stats["examples"].append({
                            "file": fname, "question": qnum,
                            "option": first_key,
                            "original": options.get(first_key, ""),
                            "latex": result[first_key],
                        })

                    print(f"-> {len(result)}/{len(to_c)} converted", flush=True)
                except Exception as e:
                    stats["errors"].append(f"{fname} Q{qnum} options: {str(e)[:100]}")
                    print(f"-> ERROR: {e}", flush=True)
                    options_latex = dict(options)

                time.sleep(RATE_LIMIT_DELAY)
                q["options_latex"] = options_latex
            else:
                q["options_latex"] = dict(options)

            # --- Convert question_text ---
            qt = q.get("question_text", "")
            if needs_conversion(qt):
                try:
                    qt_latex = convert_text_field(qt, f"Module: {data.get('module', '')}")
                    if qt_latex:
                        q["question_text_latex"] = qt_latex
                        stats["question_text_converted"] += 1
                    time.sleep(RATE_LIMIT_DELAY)
                except Exception as e:
                    stats["errors"].append(f"{fname} Q{qnum} qt: {str(e)[:100]}")

            # --- Convert question_images descriptions ---
            qi = q.get("question_images", [])
            qi_latex = []
            for img in qi:
                desc = ""
                if isinstance(img, dict):
                    desc = img.get("description", "") or img.get("alt", "") or ""
                elif isinstance(img, str):
                    desc = img

                if needs_conversion(desc):
                    try:
                        desc_latex = convert_text_field(desc, qt[:200])
                        qi_latex.append(desc_latex if desc_latex else desc)
                        time.sleep(RATE_LIMIT_DELAY)
                    except Exception as e:
                        qi_latex.append(desc)
                        stats["errors"].append(f"{fname} Q{qnum} qi: {str(e)[:100]}")
                else:
                    qi_latex.append(desc)

            if qi and qi_latex:
                q["question_images_latex"] = qi_latex

        # Save
        with open(fpath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        stats["files_processed"] += 1
        print(f"  -> Saved {fname}")

    # --- Report ---
    print(f"\n{'='*60}")
    print("CONVERSION COMPLETE")
    print(f"{'='*60}")
    print(f"Files processed:     {stats['files_processed']}")
    print(f"Questions total:     {stats['questions_total']}")
    print(f"Questions w/ math:   {stats['questions_with_math']}")
    print(f"Options converted:   {stats['options_converted']}")
    print(f"Question texts:     {stats['question_text_converted']}")
    print(f"Errors:             {len(stats['errors'])}")

    if stats["errors"]:
        print("\nErrors:")
        for err in stats["errors"]:
            print(f"  - {err}")

    if stats["examples"]:
        print("\nExample conversions:")
        for ex in stats["examples"]:
            print(f"\n  {ex['file']} Q{ex['question']} Option {ex['option']}:")
            print(f"    BEFORE: {ex['original']}")
            print(f"    AFTER:  {ex['latex']}")


if __name__ == "__main__":
    main()
