#!/usr/bin/env python3
"""
Fix question_text field in ESAT specimen questions — remove leaked option text.

Problem: question_text contains the option values at the end, which should
only be in the `options` dict. This script strips those leaked options.

Strategy:
1. For questions ending with option values: find the last occurrence of any
   option value and trim everything from that point onwards.
2. For questions ending with option letters (A, B, C... on separate lines):
   find the contiguous block of single-letter lines matching option keys at
   the end and remove them.
3. For "Which of the following" questions with numbered stems (1. 2. 3. 4.):
   keep the numbered items but remove the letter-based option combos that
   follow.
"""

import json
import os
import re
import sys

CORPUS_DIR = os.path.join(os.path.dirname(__file__), '..', 'json', 'esat')


def get_option_strings(options):
    """Get all option values, sorted by length descending for greedy matching."""
    return sorted(options.values(), key=len, reverse=True)


def get_option_keys(options):
    """Get option keys as a set."""
    return set(options.keys())


def strip_leaked_option_values(text, option_strings):
    """
    Strip leaked option values from the end of question_text.
    
    Strategy: Working from the end, find lines that match option values
    and remove them (plus any blank lines before them).
    """
    lines = text.split('\n')
    
    # Build reversed list of non-empty lines to find where options start
    # We need to identify a contiguous block of option values at the end
    stripped_indices = set()
    
    # Check from the end backwards
    i = len(lines) - 1
    # Skip trailing whitespace-only lines
    while i >= 0 and lines[i].strip() == '':
        i -= 1
    
    # Now try to match option values from bottom up
    while i >= 0:
        stripped_line = lines[i].strip()
        if stripped_line == '':
            # Blank line in the middle of options — skip but continue
            i -= 1
            continue
        
        # Check if this line matches any option value
        matched = False
        for opt_val in option_strings:
            if stripped_line == opt_val:
                stripped_indices.add(i)
                matched = True
                break
        
        if matched:
            i -= 1
        else:
            # This line doesn't match an option — stop
            break
    
    if not stripped_indices:
        return None  # No change needed
    
    # Find the lowest index to strip from (remove contiguous block + trailing blanks)
    min_idx = min(stripped_indices)
    
    # Also remove any blank lines just before the first stripped line
    j = min_idx - 1
    while j >= 0 and lines[j].strip() == '':
        j -= 1
    
    new_text = '\n'.join(lines[:j + 1])
    return new_text


def strip_leaked_option_letters(text, option_keys):
    """
    Strip leaked option letters (A, B, C, D...) from the end.
    
    These appear as single lines each containing just a letter like "A", "B", etc.
    The block is contiguous at the end of the text.
    """
    lines = text.split('\n')
    
    # Find contiguous block of single-letter option keys at the end
    stripped_indices = set()
    
    i = len(lines) - 1
    while i >= 0:
        stripped_line = lines[i].strip()
        if stripped_line == '':
            i -= 1
            continue
        if stripped_line in option_keys and len(stripped_line) == 1:
            stripped_indices.add(i)
            i -= 1
        else:
            break
    
    if not stripped_indices:
        return None
    
    min_idx = min(stripped_indices)
    
    # Remove blank lines before the block
    j = min_idx - 1
    while j >= 0 and lines[j].strip() == '':
        j -= 1
    
    new_text = '\n'.join(lines[:j + 1])
    return new_text


def fix_question_text(q):
    """
    Attempt to fix a single question's question_text.
    Returns (new_text, description) or None if no fix needed.
    """
    qt = q['question_text']
    options = q['options']
    option_strings = get_option_strings(options)
    option_keys = get_option_keys(options)
    
    # Check if the text ends with an option value
    ends_with_value = any(qt.strip().endswith(v) for v in option_strings)
    
    # Check if the last non-empty line is an option letter
    lines = [l.strip() for l in qt.strip().split('\n') if l.strip()]
    ends_with_letter = bool(lines) and lines[-1] in option_keys and len(lines[-1]) == 1
    
    if not ends_with_value and not ends_with_letter:
        return None
    
    if ends_with_value:
        new_text = strip_leaked_option_values(qt, option_strings)
    elif ends_with_letter:
        new_text = strip_leaked_option_letters(qt, option_keys)
    
    if new_text is None or new_text == qt:
        return None
    
    return new_text


def verify_fix(q, original_text):
    """Verify a fix is valid. Returns list of warning strings."""
    warnings = []
    new_text = q['question_text']
    options = q['options']
    
    # Check no option value remains in the text
    for key, val in options.items():
        if val in new_text:
            # Check if it's in the stem part (before any question mark area)
            # or if it's truly leaked — we allow if the option text also appears
            # in legitimate question context
            # For short/common values, this is expected
            if len(val) > 3:
                warnings.append(f"Option {key} value still in text: '{val[:60]}'")
    
    # Check question still has a question mark or is a statement
    if '?' not in new_text and not new_text.strip().endswith(':'):
        warnings.append("No question mark found in cleaned text")
    
    # Check we didn't remove too much (new text should be at least 30% of original)
    if len(new_text) < 0.3 * len(original_text):
        warnings.append(f"Removed >70% of text ({len(original_text)} -> {len(new_text)} chars)")
    
    return warnings


def main():
    total_questions = 0
    modified = 0
    unchanged = 0
    flagged = []
    
    all_files = sorted(f for f in os.listdir(CORPUS_DIR) if f.endswith('.json'))
    
    for filename in all_files:
        filepath = os.path.join(CORPUS_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        file_modified = False
        
        for q in data['questions']:
            total_questions += 1
            qid = q['id']
            original = q['question_text']
            
            result = fix_question_text(q)
            if result is not None:
                q['question_text'] = result
                modified += 1
                file_modified = True
                
                # Verify
                warnings = verify_fix(q, original)
                if warnings:
                    flagged.append((qid, warnings))
                
                # Print diff
                old_end = original[-100:].replace('\n', '\\n')
                new_end = result[-100:].replace('\n', '\\n')
                print(f"\n  ✏️  {qid}:")
                print(f"     OLD (last 100): ...{old_end}")
                print(f"     NEW (last 100): ...{new_end}")
                if warnings:
                    for w in warnings:
                        print(f"     ⚠️  {w}")
            else:
                unchanged += 1
        
        if file_modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n  💾 Saved: {filename}")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total questions: {total_questions}")
    print(f"Modified:        {modified}")
    print(f"Unchanged:       {unchanged}")
    if flagged:
        print(f"\n⚠️  Flagged ({len(flagged)} questions with warnings):")
        for qid, warnings in flagged:
            print(f"  - {qid}: {', '.join(warnings)}")
    else:
        print("\n✅ All modifications passed verification.")


if __name__ == '__main__':
    main()
