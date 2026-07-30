#!/usr/bin/env python3
"""
Clean reset and re-derivation of ALL correct_answer fields.
Strategy:
1. Clear all correct_answer fields
2. Re-derive from explanation text using carefully validated patterns
3. Also try raw image/plain text matching from extraction data
4. Save results
"""

import json
import re
import sys
from pathlib import Path

JSON_DIR = Path("/home/ubuntu/.paperclip/esat-shared/corpus/json/esat")


def normalize_text(text):
    if not text:
        return ""
    t = text.lower().strip()
    t = t.replace('\u2009', ' ').replace('\xa0', ' ')
    t = re.sub(r'[°º]', ' degree ', t)
    t = re.sub(r'[\u2013\u2014]', '-', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def normalize_aggressive(text):
    if not text:
        return ""
    t = text.lower().strip()
    t = t.replace('\u2009', '').replace('\xa0', '')
    t = re.sub(r'[°º\u2013\u2014\.\,\;\:\!\?\(\)\[\]\{\}]', '', t)
    t = re.sub(r'\s+', '', t)
    return t


def normalize_alt_text(text):
    """Normalize math alt text for comparison."""
    if not text:
        return ""
    t = text.lower().strip()
    for token in ['begin mathsize 16px style', 'end style', 'begin mathsize 12px style',
                  'begin inline style', 'end inline style', 'begin display style', 'end display style']:
        t = t.replace(token, '')
    t = t.replace(' space ', ' ').replace(' space', ' ').replace('space ', ' ')
    t = t.replace('straight ', '')
    for token in ['blank', 'presubscript', 'presuperscript']:
        t = t.replace(token, '')
    t = re.sub(r'\s+', '', t)
    replacements = {
        'degree': '°', 'plus': '+', 'minus': '-', 'times': '×',
        'dividedby': '÷', 'lessthan': '<', 'greaterthan': '>',
        'greaterorequalthan': '≥', 'lessorequalthan': '≤',
        'equals': '=', 'notequalto': '≠', 'approximatelyequalto': '≈',
    }
    for word, sym in replacements.items():
        t = t.replace(word, sym)
    return t


def derive_answer(q):
    """Derive correct answer from question data using all available info."""
    options = q.get('options', {})
    if not options:
        return ("", 0, "no_options")
    
    explanation = q.get('explanation', '')
    correct_raw = q.get('correct_answer_raw', '')
    correct_plain = q.get('correct_answer_plain', '')
    correct_images = q.get('correct_answer_images', [])
    expl_images = q.get('explanation_images', [])
    
    expl_lower = explanation.lower() if explanation else ""
    
    # === High-confidence patterns ===
    
    # Pattern 1: "The answer is option X" (direct letter reference)
    m = re.search(r'the answer is option\s+([a-h])\b', expl_lower)
    if m:
        letter = m.group(1).upper()
        if letter in options:
            return (letter, 100, "option_letter")
    
    # Pattern 2: "The answer is X." where X is a single letter at end of sentence
    # Must NOT match articles (e.g., "The answer is a 49% decrease")
    m = re.search(r'the answer is:?\s+([a-h])\s*[\.\;\n]', expl_lower)
    if m:
        letter = m.group(1).upper()
        if letter in options:
            return (letter, 100, "direct_letter_period")
    
    # Pattern 2b: "The answer is row X"
    m = re.search(r'the (?:correct )?answer is row\s+([a-h])\b', expl_lower)
    if m:
        letter = m.group(1).upper()
        if letter in options:
            return (letter, 100, "row_letter")
    
    # Pattern 3: "The answer is: [exact option text]" — exact match
    m = re.search(r'the (?:correct )?answer is:?\s*(.+?)(?:\.|$)', explanation, re.IGNORECASE | re.MULTILINE)
    if m:
        answer_text = m.group(1).strip().rstrip('.')
        answer_norm = normalize_aggressive(answer_text)
        if answer_norm and len(answer_norm) >= 2:
            # EXACT match only
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if opt_norm and opt_norm == answer_norm:
                    return (letter, 100, "exact_text")
    
    # Pattern 4: "option X" in correct_answer_plain
    if correct_plain:
        m = re.match(r'option\s+([a-h])\b', correct_plain, re.IGNORECASE)
        if m:
            letter = m.group(1).upper()
            if letter in options:
                return (letter, 100, "plain_option")
    
    # Pattern 5: Variable matching (a=-5, b=9 → option "a equals negative 5")
    for letter, opt_text in options.items():
        opt_lower = opt_text.lower()
        opt_vars = {}
        for m_var in re.finditer(r'([a-z])\s+equals\s+(?:negative\s+|minus\s+)?(\d+(?:\.\d+)?)', opt_lower):
            prefix = opt_lower[m_var.start():m_var.start()+40]
            is_neg = 'negative' in prefix or 'minus' in prefix
            opt_vars[m_var.group(1)] = ('-' + m_var.group(2) if is_neg else m_var.group(2))
        if not opt_vars:
            continue
        all_found = True
        for var, opt_val in opt_vars.items():
            abs_val = opt_val.lstrip('-')
            patterns = [
                rf'{var}\s*=\s*-?{re.escape(abs_val)}\b',
                rf'{var}\s*=\s*\u2212?{re.escape(abs_val)}\b',
                rf'{var}\s+equals\s+(?:negative\s+)?{re.escape(abs_val)}',
            ]
            found = any(re.search(p, expl_lower) for p in patterns)
            if not found:
                all_found = False
                break
        if all_found:
            return (letter, 95, "variable_match")
    
    # Pattern 6: Token matching for statement-combo options ("1 and 2 only" etc.)
    m = re.search(r'the answer is:?\s*(.+?)\.?\s*(?:\n|$)', explanation, re.IGNORECASE)
    if m:
        answer_text = m.group(1).strip().rstrip('.')
        answer_tokens = set(re.findall(r'\d+', answer_text))
        if answer_tokens:
            answer_lower = answer_text.lower()
            for letter, opt_text in options.items():
                opt_tokens = set(re.findall(r'\d+', opt_text))
                if opt_tokens and answer_tokens == opt_tokens:
                    if 'only' in answer_lower and 'only' in opt_text.lower():
                        return (letter, 95, "token_only_match")
                    if 'none' in answer_lower and 'none' in opt_text.lower():
                        return (letter, 95, "token_none_match")
    
    # === Medium-confidence patterns ===
    
    # Pattern 7: "so the answer is X" / "the correct answer is X" within sentence
    m = re.search(r'(?:so |thus |therefore |and so )?(?:the )?(?:correct )?answer is\s+(.+?)(?:\.|,|$)', explanation, re.IGNORECASE | re.MULTILINE)
    if m:
        answer_text = m.group(1).strip().rstrip('.,')
        answer_norm = normalize_aggressive(answer_text)
        if answer_norm:
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if opt_norm and opt_norm == answer_norm:
                    return (letter, 90, "sentence_exact")
    
    # Pattern 8: Raw alt-text matching (from extraction data)
    all_images = []
    if correct_raw:
        all_images.append(correct_raw)
    if correct_images:
        all_images.extend(correct_images[:3])
    
    for img_text in all_images:
        img_norm = normalize_alt_text(img_text)
        if not img_norm or len(img_norm) < 3:
            continue
        for letter, opt_text in options.items():
            opt_detailed = q.get('options_detailed', {}).get(letter, {})
            if not isinstance(opt_detailed, dict):
                continue
            for alt in opt_detailed.get('math_alt', []):
                alt_norm = normalize_alt_text(alt)
                if not alt_norm:
                    continue
                if alt_norm == img_norm:
                    return (letter, 90, "alt_exact")
                # For shorter normalized strings (like isotope notation), use substring
                min_len = min(len(alt_norm), len(img_norm))
                if min_len >= 3:
                    if alt_norm in img_norm or img_norm in alt_norm:
                        # For isotope notation like "1737" vs "1737", this is exact
                        # For "1737" in a longer string, be more careful
                        if min_len >= 4:
                            return (letter, 85, "alt_substring")
                        elif min_len >= 3 and len(alt_norm) == len(img_norm):
                            return (letter, 85, "alt_substring")
    
    # Pattern 9: Numeric matching from "The answer is [number] [unit]"
    m = re.search(r'the answer is:?	?\s+(\d+\.?\d*)\s*([a-zA-Z°²³¹⁻⁺/]*)', expl_lower)
    if m:
        try:
            answer_num = float(m.group(1))
            for letter, opt_text in options.items():
                # Use plain_text from options_detailed if available to avoid matching mathsize numbers
                opt_detailed = q.get('options_detailed', {}).get(letter, {})
                opt_plain = opt_detailed.get('plain_text', '') if isinstance(opt_detailed, dict) else ''
                search_text = opt_plain or opt_text
                # Find ALL numbers and match any
                opt_nums = re.findall(r'(\d+\.?\d*)', search_text)
                for opt_num_str in opt_nums:
                    try:
                        if float(opt_num_str) == answer_num:
                            return (letter, 85, "numeric_exact")
                            break
                    except ValueError:
                        pass
        except ValueError:
            pass
    
    # Pattern 10: "In case X" for letter-only options
    if all(len(v.strip()) <= 2 for v in options.values()):
        case_matches = re.findall(r'(?:in |for )?case\s+([a-h])\b', expl_lower)
        if case_matches:
            for case_letter in case_matches:
                idx = expl_lower.find(f'case {case_letter}')
                context = expl_lower[max(0,idx-50):idx+200]
                if any(kw in context for kw in ['same', 'correct', 'no change', 'does not change', 'equal']):
                    if case_letter.upper() in options:
                        return (case_letter.upper(), 85, "case_context")
            unique_cases = list(dict.fromkeys(case_matches))
            if len(unique_cases) == 1:
                return (unique_cases[0].upper(), 80, "case_unique")
    
    # Pattern 11: Numeric extraction from explanation tail
    lines = explanation.split('\n') if explanation else []
    last_5_lines = ' '.join(lines[-5:]) if len(lines) >= 5 else explanation
    # Also capture sign before the number
    numbers_in_tail = re.findall(r'(?:=|is|equals|gives)\s*([+\-\u2212]?)\s*(\d+\.?\d*)\s*([a-zA-Z°²³¹⁻⁺/]*)', last_5_lines, re.IGNORECASE)
    if numbers_in_tail:
        for sign, num_str, unit in reversed(numbers_in_tail):
            try:
                num = float(num_str)
                is_positive = sign in ['+', '']
                for letter, opt_text in options.items():
                    opt_detailed = q.get('options_detailed', {}).get(letter, {})
                    opt_plain = opt_detailed.get('plain_text', '') if isinstance(opt_detailed, dict) else ''
                    search_text = opt_plain or opt_text
                    # Check sign matches
                    opt_is_positive = '+' in search_text[:3] or '−' not in search_text[:3] and '-' not in search_text[:3]
                    opt_nums = re.findall(r'(\d+\.?\d*)', search_text)
                    for opt_num_str in opt_nums:
                        try:
                            if abs(float(opt_num_str) - num) < 0.01 * max(abs(num), 1):
                                # Verify sign matches for large numbers
                                if num >= 50:
                                    opt_has_neg = '−' in search_text[:3] or search_text.strip().startswith('-')
                                    if is_positive and opt_has_neg:
                                        continue  # Wrong sign, skip
                                    if not is_positive and not opt_has_neg:
                                        continue  # Wrong sign, skip
                                return (letter, 75, "numeric_tail")
                        except ValueError:
                            pass
            except ValueError:
                pass
    
    # Pattern 12: Substring matching (lower confidence)
    m = re.search(r'the (?:correct )?answer is:?\s*(.+?)(?:\.|$)', explanation, re.IGNORECASE | re.MULTILINE)
    if m:
        answer_text = m.group(1).strip().rstrip('.')
        answer_norm = normalize_aggressive(answer_text)
        if answer_norm and len(answer_norm) >= 4:
            best_match = ""
            best_score = 0
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if not opt_norm or len(opt_norm) < 3:
                    continue
                if opt_norm in answer_norm and len(opt_norm) >= 5:
                    score = len(opt_norm)
                    if score > best_score:
                        best_score = score
                        best_match = letter
            if best_match:
                return (best_match, 70, "substring_match")
    
    # Pattern 13: Plain text matching from extraction data
    if correct_plain:
        plain_norm = normalize_aggressive(correct_plain)
        if plain_norm and len(plain_norm) >= 2:
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if opt_norm and opt_norm == plain_norm:
                    return (letter, 85, "plain_exact")
        # Plain numeric match
        plain_num_match = re.search(r'(\d+\.?\d*)', correct_plain)
        if plain_num_match:
            try:
                plain_num = float(plain_num_match.group(1))
                for letter, opt_text in options.items():
                    opt_detailed = q.get('options_detailed', {}).get(letter, {})
                    opt_plain = opt_detailed.get('plain_text', '') if isinstance(opt_detailed, dict) else ''
                    search_text = opt_plain or opt_text
                    opt_nums = re.findall(r'(\d+\.?\d*)', search_text)
                    for opt_num_str in opt_nums:
                        try:
                            if abs(float(opt_num_str) - plain_num) < 0.01 * max(abs(plain_num), 1):
                                return (letter, 80, "plain_numeric")
                        except ValueError:
                            pass
            except ValueError:
                pass
    
    # Pattern 14: "It is not possible that: [option text]" — the answer IS that option
    m = re.search(r'it is not possible that:?	?\s*(.+?)(?:\.|\n|$)', expl_lower)
    if m:
        negated_text = m.group(1).strip().rstrip('.')
        neg_norm = normalize_aggressive(negated_text)
        if neg_norm and len(neg_norm) >= 5:
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if opt_norm and opt_norm == neg_norm:
                    return (letter, 90, "not_possible_exact")
                if len(opt_norm) >= 10 and len(neg_norm) >= 10:
                    if opt_norm in neg_norm or neg_norm in opt_norm:
                        return (letter, 80, "not_possible_substr")
    
    # Pattern 15: Cross-reference explanation images against option alts
    # (answer appears in both explanation solution and options)
    if expl_images:
        matches = []
        for img_alt in expl_images:
            img_norm = normalize_alt_text(img_alt)
            if not img_norm or len(img_norm) < 8:
                continue
            for letter, opt_text in options.items():
                opt_detailed = q.get('options_detailed', {}).get(letter, {})
                if not isinstance(opt_detailed, dict):
                    continue
                for opt_alt in opt_detailed.get('math_alt', []):
                    opt_norm = normalize_alt_text(opt_alt)
                    if not opt_norm:
                        continue
                    if img_norm == opt_norm:
                        matches.append(letter)
                        break
                    if len(img_norm) > 10 and len(opt_norm) > 10:
                        if img_norm in opt_norm or opt_norm in img_norm:
                            matches.append(letter)
                            break
        unique_matches = list(set(matches))
        if len(unique_matches) == 1:
            return (unique_matches[0], 75, "expl_image_cross_ref")
    
    return ("", 0, "no_match")


def main():
    modules = ['maths1', 'maths2', 'physics', 'chemistry', 'biology']
    
    total = 0
    total_answered = 0
    method_counts = {}
    unmatched = []
    
    for module in modules:
        json_file = JSON_DIR / f"esat_specimen_{module}.json"
        if not json_file.exists():
            continue
        
        with open(json_file) as f:
            data = json.load(f)
        
        module_answered = 0
        for q in data.get('questions', []):
            total += 1
            
            # Clear existing answer
            old_answer = q.get('correct_answer', '')
            q['correct_answer'] = ''
            
            answer, confidence, method = derive_answer(q)
            
            if answer:
                q['correct_answer'] = answer
                total_answered += 1
                module_answered += 1
                method_counts[method] = method_counts.get(method, 0) + 1
            else:
                unmatched.append(f"{module} Q{q['question_number']}")
        
        # Save
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"{module}: {module_answered}/{len(data.get('questions', []))} answered")
    
    # Update combined
    combined = {}
    for module in modules:
        json_file = JSON_DIR / f"esat_specimen_{module}.json"
        if json_file.exists():
            with open(json_file) as f:
                combined[module] = json.load(f)
    with open(JSON_DIR / "esat_specimen_all.json", 'w') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    
    print(f"\nTotal: {total_answered}/{total} answered")
    print(f"Methods: {method_counts}")
    if unmatched:
        print(f"Unmatched: {unmatched}")


if __name__ == '__main__':
    main()
