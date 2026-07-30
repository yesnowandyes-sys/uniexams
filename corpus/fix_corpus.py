#!/usr/bin/env python3
"""Fix corpus extraction issues across all JSON files."""

import json, glob, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(BASE, 'json')

def clean_text(text):
    """Clean OCR artifacts from text."""
    if not isinstance(text, str):
        return text
    
    # Strip control characters except newline, tab, carriage return
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    
    # Fix specific patterns
    # ௗ followed by unit + ௗ -> just keep the unit (ௗ was a superscript marker)
    # e.g. "1.0ௗNௗcmí1" -> "1.0 N cm⁻¹"
    text = text.replace('ௗ', '')  # Remove Tamil artifacts
    
    # í1 -> ⁻¹ (superscript -1)
    text = text.replace('í1', '⁻¹')
    text = text.replace('í2', '⁻²')
    text = text.replace('í3', '⁻³')
    
    # ȍ -> Ω (ohms)
    text = text.replace('ȍ', 'Ω')
    
    # ֖ or ֖\x03 -> ↔ (equilibrium/reversible reaction)
    text = text.replace('֖\x03', '⇌')
    text = text.replace('֖', '⇌')
    
    # ǻ -> Δ (delta)
    text = text.replace('ǻ', 'Δ')
    
    # Collapse excessive whitespace (but keep single newlines)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Clean up space before punctuation
    text = re.sub(r' ([,.:;!?])', r'\1', text)
    
    return text.strip()

def fix_nsaa_s2_corruption():
    """Fix OCR corruption in NSAA S2 files."""
    fixed = 0
    for f in sorted(glob.glob(os.path.join(JSON_DIR, 'nsaa_s2', '*.json'))):
        with open(f) as fh:
            data = json.load(fh)
        qs = data if isinstance(data, list) else data.get('questions', [])
        modified = False
        for q in qs:
            if isinstance(q, str):
                continue
            qt = q.get('question_text', '')
            cleaned = clean_text(qt)
            if cleaned != qt:
                q['question_text'] = cleaned
                modified = True
                fixed += 1
            opts = q.get('options', {})
            cleaned_opts = {}
            for k, v in opts.items():
                cv = clean_text(v)
                if cv != v:
                    cleaned_opts[k] = cv
                else:
                    cleaned_opts[k] = v
            if cleaned_opts != opts:
                q['options'] = cleaned_opts
                modified = True
        if modified:
            with open(f, 'w') as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            print(f"  Fixed {f}")
    return fixed

def fix_tmua_corruption():
    """Fix OCR corruption in TMUA files."""
    fixed = 0
    for f in sorted(glob.glob(os.path.join(JSON_DIR, 'tmua', '*.json'))):
        with open(f) as fh:
            data = json.load(fh)
        modified = False
        for q in data:
            if isinstance(q, str):
                continue
            qt = q.get('question_text', '')
            cleaned = clean_text(qt)
            if cleaned != qt:
                q['question_text'] = cleaned
                modified = True
                fixed += 1
            opts = q.get('options', {})
            cleaned_opts = {}
            for k, v in opts.items():
                cv = clean_text(v)
                if cv != v:
                    cleaned_opts[k] = cv
                else:
                    cleaned_opts[k] = v
            if cleaned_opts != opts:
                q['options'] = cleaned_opts
                modified = True
        if modified:
            with open(f, 'w') as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            print(f"  Fixed {f}")
    return fixed

def clean_all_whitespace():
    """Collapse excessive whitespace in question_text and options across all files."""
    fixed = 0
    for pattern in ['engaa/*.json', 'nsaa/*.json', 'nsaa_s2/*.json', 'tmua/*.json', 'esat/*.json']:
        for f in sorted(glob.glob(os.path.join(JSON_DIR, pattern))):
            with open(f) as fh:
                data = json.load(fh)
            qs = data if isinstance(data, list) else data.get('questions', [])
            modified = False
            for q in qs:
                if isinstance(q, str):
                    continue
                for field in ['question_text']:
                    val = q.get(field, '')
                    if isinstance(val, str):
                        cleaned = re.sub(r' {2,}', ' ', val)
                        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
                        if cleaned != val:
                            q[field] = cleaned
                            modified = True
                            fixed += 1
                opts = q.get('options', {})
                for k, v in opts.items():
                    if isinstance(v, str):
                        cleaned = re.sub(r' {2,}', ' ', v)
                        if cleaned != v:
                            opts[k] = cleaned
                            modified = True
            if modified:
                with open(f, 'w') as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
    return fixed

if __name__ == '__main__':
    print("=== Issue 1: Fixing OCR corruption ===")
    print("\nNSAA S2:")
    nsaa_fixed = fix_nsaa_s2_corruption()
    print(f"  Fixed {nsaa_fixed} questions")
    
    print("\nTMUA:")
    tmua_fixed = fix_tmua_corruption()
    print(f"  Fixed {tmua_fixed} questions")
    
    print("\nWhitespace cleanup across all files:")
    ws_fixed = clean_all_whitespace()
    print(f"  Cleaned {ws_fixed} fields")
    
    print("\nDone.")
