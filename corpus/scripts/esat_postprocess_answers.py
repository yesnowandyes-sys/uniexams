#!/usr/bin/env python3
"""
Post-process ESAT specimen JSONs to fill in missing correct_answer fields.
Uses improved text matching from explanation text.
"""

import json
import re
import sys
from pathlib import Path

JSON_DIR = Path("/home/ubuntu/.paperclip/esat-shared/corpus/json/esat")


def normalize_text(text):
    """Aggressively normalize text for comparison."""
    if not text:
        return ""
    t = text.lower().strip()
    t = t.replace('\u2009', ' ').replace('\xa0', ' ')  # thin space, nbsp
    # Remove units and special chars
    t = re.sub(r'[°º]', ' degree ', t)
    t = re.sub(r'[\u2013\u2014]', '-', t)  # en/em dash to hyphen
    # Remove spaces around superscript/subscript markers
    t = t.strip()
    # Normalize whitespace
    t = re.sub(r'\s+', ' ', t)
    return t


def normalize_aggressive(text):
    """Very aggressive normalization for fuzzy matching."""
    if not text:
        return ""
    t = text.lower().strip()
    t = t.replace('\u2009', '').replace('\xa0', '')
    t = re.sub(r'[°º\u2013\u2014\.\,\;\:\!\?\(\)\[\]\{\}]', '', t)
    t = re.sub(r'\s+', '', t)
    return t


def extract_answer_from_explanation(explanation, options):
    """Try many patterns to extract the correct answer from explanation text."""
    
    if not explanation:
        return ""
    
    expl = explanation
    expl_lower = expl.lower()
    
    # Pattern 1: "The answer is option X" (direct letter)
    m = re.search(r'the answer is option\s+([A-H])\b', expl_lower)
    if m:
        letter = m.group(1).upper()
        if letter in options:
            return letter
    
    # Pattern 2: "The answer is X" where X is a single letter A-H
    # Must not match articles: "The answer is a decrease" should NOT match
    m = re.search(r'the answer is:?\s+([a-h])[\.\;\n\r]|the answer is:?\s+([a-h])$', expl_lower)
    if m:
        letter = (m.group(1) or m.group(2) or '').upper()
        if letter in options:
            return letter
    
    # Pattern 2b: "The answer is row X" or "The correct answer is row X"
    m = re.search(r'the (?:correct )?answer is row\s+([a-h])\b', expl_lower)
    if m:
        letter = m.group(1).upper()
        if letter in options:
            return letter
    
    # Pattern 2c: "In case X" (for questions with labelled options A-H)
    # When options are just letters (diagrams/graphs), the explanation references cases
    if all(len(v.strip()) <= 2 for v in options.values()):
        # Find all "case X" or "In case X" references in explanation
        case_matches = re.findall(r'(?:in |for )?case\s+([a-h])\b', expl_lower)
        if case_matches:
            # The answer is typically the case that's described as matching or being correct
            # Look for the case that's described as correct/same/no change
            for case_letter in case_matches:
                # Check if this case is described as correct
                idx = expl_lower.find(f'case {case_letter.lower()}')
                context = expl_lower[max(0,idx-50):idx+200]
                if any(kw in context for kw in ['same', 'correct', 'no change', 'does not change', 'equal']):
                    if case_letter.upper() in options:
                        return case_letter.upper()
            # If only one case is mentioned, that's likely the answer
            unique_cases = list(dict.fromkeys(case_matches))
            if len(unique_cases) == 1:
                return unique_cases[0].upper()
    
    # Pattern 2d: For questions where the explanation derives values like a=-5, b=9
    # Match derived variable values to option alt-text
    # Strategy: find option-specific variable=value patterns in the explanation
    for letter, opt_text in options.items():
        opt_lower = opt_text.lower()
        # Extract variable assignments from the OPTION text
        # e.g., "[a equals negative 5 comma space space b equals 9]" → {a: -5, b: 9}
        opt_vars = {}
        # Pattern: "X equals negative Y" or "X equals Y"
        for m in re.finditer(r'([a-z])\s+equals\s+(?:negative\s+|minus\s+)?(\d+(?:\.\d+)?)', opt_lower):
            opt_vars[m.group(1)] = ('-' + m.group(2) if 'negative' in opt_lower[m.start():m.start()+30] or 'minus' in opt_lower[m.start():m.start()+30] else m.group(2))
        if not opt_vars:
            continue
        # Check all option vars appear in explanation with same values
        all_found = True
        for var, opt_val in opt_vars.items():
            # Look for this var=value in explanation
            # Handle both ASCII and unicode minus
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
            return letter
    
    # Pattern 3: "The answer is: [descriptive text]" or "The answer is [text]"
    # Try to match the descriptive text to an option
    m = re.search(r'the (?:correct )?answer is:?\s*(.+?)(?:\.|$)', expl, re.IGNORECASE | re.MULTILINE)
    if m:
        answer_text = m.group(1).strip().rstrip('.')
        answer_norm = normalize_aggressive(answer_text)
        if answer_norm:
            # Try exact match against each option
            best_match = ""
            best_score = 0
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if not opt_norm:
                    continue
                if opt_norm == answer_norm:
                    return letter
                # Substring match
                if len(opt_norm) >= 3 and len(answer_norm) >= 3:
                    if opt_norm in answer_norm or answer_norm in opt_norm:
                        score = min(len(opt_norm), len(answer_norm))
                        if score > best_score:
                            best_score = score
                            best_match = letter
            if best_match:
                return best_match
    
    # Pattern 4: "so the (correct )?answer is [value]" or "and so the answer is [value]"
    m = re.search(r'(?:so |thus |therefore |and so )?(?:the )?(?:correct )?answer is\s+(.+?)(?:\.|,|$)', expl, re.IGNORECASE | re.MULTILINE)
    if m:
        answer_text = m.group(1).strip().rstrip('.,')
        answer_norm = normalize_aggressive(answer_text)
        if answer_norm:
            best_match = ""
            best_score = 0
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if not opt_norm:
                    continue
                if opt_norm == answer_norm:
                    return letter
                if len(opt_norm) >= 2:
                    if opt_norm in answer_norm or answer_norm in opt_norm:
                        score = min(len(opt_norm), len(answer_norm))
                        if score > best_score:
                            best_score = score
                            best_match = letter
            if best_match:
                return best_match
    
    # Pattern 5: Extract numeric answer and match to option with same number
    # e.g., "The answer is 0.75 cm s–1" → find option containing "0.75"
    m = re.search(r'(?:the (?:correct )?answer is|the answer is:?)\s+(.+?)(?:\n|\.|$)', expl, re.IGNORECASE)
    if m:
        answer_text = m.group(1).strip()
        # Extract first number from answer
        num_match = re.search(r'(\d+\.?\d*)', answer_text)
        if num_match:
            answer_num = num_match.group(1)
            for letter, opt_text in options.items():
                opt_num_match = re.search(r'(\d+\.?\d*)', opt_text)
                if opt_num_match:
                    try:
                        if float(opt_num_match.group(1)) == float(answer_num):
                            return letter
                    except ValueError:
                        pass
    
    # Pattern 6: For questions where options are statement combos like "1 and 2 only"
    # The explanation says "The answer is: 1 and 2 only"
    m = re.search(r'the answer is:?\s*(.+?)\.?\s*(?:\n|$)', expl, re.IGNORECASE)
    if m:
        answer_text = m.group(1).strip().rstrip('.')
        answer_norm = normalize_text(answer_text)
        for letter, opt_text in options.items():
            opt_norm = normalize_text(opt_text)
            if not opt_norm:
                continue
            # For short options like "1 only", "1 and 2 only", exact match
            if answer_norm == opt_norm:
                return letter
            # Check if all the key tokens match
            answer_tokens = set(re.findall(r'\d+', answer_text))
            opt_tokens = set(re.findall(r'\d+', opt_text))
            if answer_tokens and answer_tokens == opt_tokens:
                # Also check "only" and "none" consistency
                answer_lower = answer_text.lower()
                if 'only' in answer_lower and 'only' in opt_text.lower():
                    return letter
                if 'none' in answer_lower and 'none' in opt_text.lower():
                    return letter
    
    return ""


def extract_answer_from_raw_images(correct_raw, correct_answer_images, explanation_images, options):
    """Try to match raw alt-text/images to options."""
    
    # Collect all possible answer image texts
    all_images = []
    if correct_raw:
        all_images.append(correct_raw)
    if correct_answer_images:
        all_images.extend(correct_answer_images)
    
    for img_text in all_images:
        img_norm = normalize_aggressive(img_text)
        if not img_norm or len(img_norm) < 3:
            continue
        for letter, opt_text in options.items():
            opt_norm = normalize_aggressive(opt_text)
            if not opt_norm:
                continue
            if img_norm == opt_norm:
                return letter
            # Substring match for longer strings
            if len(img_norm) >= 6 and len(opt_norm) >= 5:
                if img_norm in opt_norm or opt_norm in img_norm:
                    return letter
    
    return ""


def match_numeric_from_explanation(explanation, options):
    """For explanations that work through the solution, extract the final numeric answer
    and match it to an option."""
    
    if not explanation:
        return ""
    
    # Look for patterns like "X = <number>" or "answer: <number>" near the end
    # The final computed value is often near the end of the explanation
    expl_lower = explanation.lower()
    
    # Find all numbers mentioned in the explanation (last few are likely the answer)
    # Try patterns like "= <number>", "is <number>", "<number> <unit>"
    lines = explanation.split('\n')
    last_5_lines = ' '.join(lines[-5:]) if len(lines) >= 5 else explanation
    
    # Extract numbers with optional units from the last part of explanation
    numbers_in_tail = re.findall(r'(?:=|is|equals|gives)\s*(\d+\.?\d*)\s*([a-zA-Z°²³¹⁻⁺/]*)', last_5_lines, re.IGNORECASE)
    
    if numbers_in_tail:
        for num_str, unit in reversed(numbers_in_tail):
            try:
                num = float(num_str)
            except ValueError:
                continue
            for letter, opt_text in options.items():
                opt_num_match = re.search(r'(\d+\.?\d*)', opt_text)
                if opt_num_match:
                    try:
                        opt_num = float(opt_num_match.group(1))
                        if abs(opt_num - num) < 0.01 * max(abs(opt_num), 1):
                            return letter
                    except ValueError:
                        pass
    
    return ""


def process_question(q):
    """Try to fill in missing correct_answer for a question."""
    if q.get('correct_answer'):
        return q  # Already has answer
    
    options = q.get('options', {})
    if not options:
        return q
    
    explanation = q.get('explanation', '')
    correct_raw = q.get('correct_answer_raw', '')
    correct_plain = q.get('correct_answer_plain', '')
    correct_images = q.get('correct_answer_images', [])
    expl_images = q.get('explanation_images', [])
    
    # Strategy 1: Handle "option X" pattern in correct_answer_plain
    if correct_plain:
        m = re.match(r'option\s+([A-H])\b', correct_plain, re.IGNORECASE)
        if m:
            letter = m.group(1).upper()
            if letter in options:
                q['correct_answer'] = letter
                q['_match_method'] = 'plain_option_letter'
                return q
    
    # Strategy 2: Extract from explanation text
    answer = extract_answer_from_explanation(explanation, options)
    if answer:
        q['correct_answer'] = answer
        q['_match_method'] = 'explanation_pattern'
        return q
    
    # Strategy 3: Match raw images to options
    answer = extract_answer_from_raw_images(correct_raw, correct_images, expl_images, options)
    if answer:
        q['correct_answer'] = answer
        q['_match_method'] = 'raw_image_match'
        return q
    
    # Strategy 4: Match plain text to options (fuzzy)
    if correct_plain:
        plain_norm = normalize_aggressive(correct_plain)
        if plain_norm:
            best_match = ""
            best_score = 0
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if not opt_norm:
                    continue
                if opt_norm == plain_norm:
                    q['correct_answer'] = letter
                    q['_match_method'] = 'plain_exact'
                    return q
                if len(opt_norm) >= 2 and len(plain_norm) >= 2:
                    if opt_norm in plain_norm or plain_norm in opt_norm:
                        score = min(len(opt_norm), len(plain_norm))
                        if score > best_score:
                            best_score = score
                            best_match = letter
            if best_match:
                q['correct_answer'] = best_match
                q['_match_method'] = 'plain_fuzzy'
                return q
    
    # Strategy 5: Numeric extraction from explanation tail
    answer = match_numeric_from_explanation(explanation, options)
    if answer:
        q['correct_answer'] = answer
        q['_match_method'] = 'numeric_tail'
        return q
    
    return q


def main():
    modules = ['maths1', 'maths2', 'physics', 'chemistry', 'biology']
    
    stats = {}
    
    for module in modules:
        json_file = JSON_DIR / f"esat_specimen_{module}.json"
        if not json_file.exists():
            print(f"  {module}: file not found")
            continue
        
        with open(json_file) as f:
            data = json.load(f)
        
        questions = data.get('questions', [])
        before = sum(1 for q in questions if q.get('correct_answer'))
        
        for q in questions:
            q = process_question(q)
        
        after = sum(1 for q in questions if q.get('correct_answer'))
        still_missing = [q['question_number'] for q in questions if not q.get('correct_answer')]
        match_methods = {}
        for q in questions:
            method = q.get('_match_method', 'original' if q.get('correct_answer') else 'none')
            match_methods[method] = match_methods.get(method, 0) + 1
            # Clean up temp field
            q.pop('_match_method', None)
        
        stats[module] = {
            'before': before,
            'after': after,
            'total': len(questions),
            'still_missing': still_missing,
            'methods': match_methods,
        }
        
        # Save updated JSON
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  {module}: {before} → {after} / {len(questions)} | still missing: {still_missing}")
        print(f"    methods: {match_methods}")
    
    # Update combined file
    combined = {}
    for module in modules:
        json_file = JSON_DIR / f"esat_specimen_{module}.json"
        if json_file.exists():
            with open(json_file) as f:
                combined[module] = json.load(f)
    
    with open(JSON_DIR / "esat_specimen_all.json", 'w') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    
    print(f"\nCombined file updated.")
    
    total_before = sum(s['before'] for s in stats.values())
    total_after = sum(s['after'] for s in stats.values())
    total_q = sum(s['total'] for s in stats.values())
    print(f"\nOverall: {total_before} → {total_after} / {total_q}")
    
    all_missing = {}
    for module, s in stats.items():
        if s['still_missing']:
            all_missing[module] = s['still_missing']
    if all_missing:
        print(f"\nStill missing correct_answer:")
        for module, qs in all_missing.items():
            print(f"  {module}: {qs}")


if __name__ == '__main__':
    main()
