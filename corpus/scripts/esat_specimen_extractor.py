#!/usr/bin/env python3
"""
ESAT Specimen Test Extraction System
=====================================
Uses Playwright to navigate Pearson VUE's test player and extract:
- Question text (from DOM)
- Answer options with math alt-text (from DOM)
- Correct answer + worked explanation (from "Explain Answer" dialog)
- Screenshots of each question

No login required. No anti-automation detected.

Usage:
    python3 esat_specimen_extractor.py [--module maths1] [--module all]
    python3 esat_specimen_extractor.py --list  # list available modules

Output:
    - JSON: corpus/json/esat/esat_specimen_<module>.json
    - Screenshots: corpus/esat_screenshots/<module>/qNN.png
"""

import asyncio
import json
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright

# ============================================================
# Configuration
# ============================================================

MODULES = {
    "maths1": {
        "url": "https://www.pearsonvue.com/us/en/redirects/uatuk/esat-mathematics1.html",
        "label": "ESAT Mathematics 1",
        "id_prefix": "ESAT-SPECIMEN-MATHS1",
    },
    "maths2": {
        "url": "https://www.pearsonvue.com/us/en/redirects/uatuk/esat-mathematics2.html",
        "label": "ESAT Mathematics 2",
        "id_prefix": "ESAT-SPECIMEN-MATHS2",
    },
    "physics": {
        "url": "https://www.pearsonvue.com/us/en/redirects/uatuk/esat-physics.html",
        "label": "ESAT Physics",
        "id_prefix": "ESAT-SPECIMEN-PHYSICS",
    },
    "chemistry": {
        "url": "https://www.pearsonvue.com/us/en/redirects/uatuk/esat-chemistry.html",
        "label": "ESAT Chemistry",
        "id_prefix": "ESAT-SPECIMEN-CHEMISTRY",
    },
    "biology": {
        "url": "https://www.pearsonvue.com/us/en/redirects/uatuk/esat-biology.html",
        "label": "ESAT Biology",
        "id_prefix": "ESAT-SPECIMEN-BIOLOGY",
    },
}

SCRIPT_DIR = Path(__file__).parent.parent  # corpus/
SCREENSHOTS_DIR = SCRIPT_DIR / "esat_screenshots"
JSON_DIR = SCRIPT_DIR / "json" / "esat"

# ============================================================
# Helpers
# ============================================================

async def navigate_via_navigator(page, target_qnum):
    """Use the Navigator panel to jump to a specific question."""
    nav_btn = await page.query_selector("button:has-text('Navigator')")
    if not nav_btn or not await nav_btn.is_visible():
        return False

    await nav_btn.click()
    await asyncio.sleep(2)

    # In Navigator, question links are <a> elements with text "Question N"
    q_link = await page.query_selector(f"a:has-text('Question {target_qnum}')")
    if not q_link:
        # Try just the number
        q_link = await page.query_selector(f"td:has-text('{target_qnum}')")

    if q_link:
        await q_link.click()
        await asyncio.sleep(2)
        return True

    # Close Navigator if target not found
    close_btns = await page.query_selector_all("button:has-text('Close')")
    for btn in close_btns:
        if await btn.is_visible():
            await btn.click()
            await asyncio.sleep(1)
            break
    return False


async def scroll_question_into_view(page):
    """Scroll through the question to satisfy the 'viewed entire screen' requirement.

    The Pearson test player requires users to scroll to all corners of the question
    before allowing navigation. Without this, it shows:
    'You have not yet viewed the entire screen...'
    """
    try:
        # Find the scrollable content area
        content = await page.query_selector("#abe-contentPane")
        if content:
            # Scroll down to bottom
            await content.evaluate("el => el.scrollTo(0, el.scrollHeight)")
            await asyncio.sleep(0.3)
            # Scroll back to top
            await content.evaluate("el => el.scrollTo(0, 0)")
            await asyncio.sleep(0.3)

        # Also scroll the main page
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(0.2)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.2)

        # Check for any tabbed content and select each tab
        tabs = await page.query_selector_all(".ui-tabs-nav li a")
        for tab in tabs:
            try:
                await tab.click(timeout=2000)
                await asyncio.sleep(0.3)
            except:
                pass
    except:
        pass


async def click_next(page):
    """Click the Next button if visible, handling any confirmation dialogs."""
    btn = await page.query_selector("button:has-text('Next')")
    if btn and await btn.is_visible():
        try:
            await btn.click(timeout=10000)
        except:
            # Force click if overlay present
            await btn.click(force=True, timeout=5000)
        await asyncio.sleep(2)

        # Handle any confirmation dialog (OK button) that may appear
        ok_btn = await page.query_selector("button:has-text('OK')")
        if ok_btn and await ok_btn.is_visible():
            await ok_btn.click(timeout=5000)
            await asyncio.sleep(2)

        return True
    return False

async def click_previous(page):
    """Click the Previous button if visible."""
    btn = await page.query_selector("button:has-text('Previous')")
    if btn and await btn.is_visible():
        await btn.click()
        await asyncio.sleep(2)
        return True
    return False

async def get_question_number(page):
    """Extract current question number from the page."""
    body_text = await page.inner_text("body")
    match = re.search(r'(\d+)\s+of\s+(\d+)', body_text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


async def extract_question_text(page):
    """Extract question text from the content pane DOM.

    Returns (text, images) where text is the question stem text
    and images is a list of math alt-text strings for images in the question.
    """
    content = await page.query_selector("#abe-contentPane")
    if not content:
        return "needs_manual_transcription", []

    # Question text is in div[leafdatatype='text'] blocks before the radio buttons
    text_parts = []
    images = []

    # Get all text blocks
    text_blocks = await content.query_selector_all("div[leafdatatype='text']")

    # We need to find where the options start. The first radio button container
    # marks the boundary. Let's check each text block.
    for block in text_blocks:
        # Check if this block is inside an option (has radio button parent)
        is_in_option = await block.evaluate("""el => {
            let p = el;
            for (let i = 0; i < 10; i++) {
                p = p.parentElement;
                if (!p) break;
                if (p.classList.contains('abe-input-container')) return true;
            }
            return false;
        }""")

        if not is_in_option:
            text = await block.inner_text()
            text = text.strip()
            if text:
                # Get math images in this block
                imgs = await block.query_selector_all("img")
                for img in imgs:
                    alt = await img.get_attribute("alt")
                    if alt:
                        images.append(alt)
                text_parts.append(text)

    combined_text = "\n".join(text_parts)
    images = list(dict.fromkeys(images))  # dedupe preserving order

    return combined_text if combined_text.strip() else "needs_manual_transcription", images


async def extract_options(page):
    """Extract answer options (A, B, C, D, E...) from the DOM.

    The test player renders options as radio buttons with associated labels.
    Option text often contains math notation as <img> tags with descriptive alt text.
    We extract both plain text and math alt text.
    """
    options = {}

    radios = await page.query_selector_all("#abe-contentPane input[type='radio']")

    for radio in radios:
        value = await radio.get_attribute("value")
        if not value:
            continue

        radio_id = await radio.get_attribute("id")
        label_text = ""
        math_alts = []

        # Strategy 1: Reader label (accessible, has alt text)
        accessible_id = f"abe-accessible-{radio_id}" if radio_id else None
        if accessible_id:
            reader_label = await page.query_selector(f"#{accessible_id}")
            if reader_label:
                label_text = await reader_label.inner_text()
                imgs = await reader_label.query_selector_all("img")
                for img in imgs:
                    alt = await img.get_attribute("alt")
                    if alt:
                        math_alts.append(alt)

        # Strategy 2: Default visible label
        if not label_text.strip() and radio_id:
            default_label = await page.query_selector(f"label[for='{radio_id}'].abe-defaultLabel")
            if default_label:
                label_text = await default_label.inner_text()
                imgs = await default_label.query_selector_all("img")
                for img in imgs:
                    alt = await img.get_attribute("alt")
                    if alt:
                        math_alts.append(alt)

        # Strategy 3: Walk up to horizontalParent
        if not label_text.strip():
            option_text = await radio.evaluate("""el => {
                let p = el;
                for (let i = 0; i < 10; i++) {
                    p = p.parentElement;
                    if (!p) break;
                    if (p.classList.contains('horizontalParent')) {
                        return p.innerText;
                    }
                }
                return el.parentElement?.parentElement?.innerText || '';
            }""")
            if option_text:
                label_text = option_text

        label_text = label_text.strip()

        # Build full text: combine math alt-text + plain text
        full_text = label_text
        for alt in math_alts:
            if alt not in full_text:
                if full_text:
                    # Math expression likely precedes unit text like "cm"
                    full_text = f"[{alt}] {full_text}"
                else:
                    full_text = f"[{alt}]"

        options[value] = {
            "text": full_text if full_text else "needs_manual_transcription",
            "math_alt": math_alts,
            "plain_text": label_text
        }

    return options


async def dismiss_dialogs(page):
    """Force-close any open dialogs or overlays using the proper Close button first."""
    # Strategy 1: Find and click the dialog Close button (proper way)
    try:
        close_btn = await page.query_selector(".ui-dialog-titlebar-close")
        if close_btn and await close_btn.is_visible():
            await close_btn.click(timeout=5000)
            await asyncio.sleep(1)
            return True
    except:
        pass

    # Strategy 2: Try clicking any visible Close button
    try:
        close_btns = await page.query_selector_all("button:has-text('Close')")
        for btn in close_btns:
            if await btn.is_visible():
                await btn.click(timeout=2000)
                await asyncio.sleep(0.5)
                return True
    except:
        pass

    # Strategy 3: Escape key
    try:
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
    except:
        pass

    return False


def normalize_alt_text(text):
    """Aggressively normalize math alt text for comparison.

    Strips formatting tokens that differ between option labels and explanation dialog
    images, so we can match them.
    """
    if not text:
        return ""
    t = text.lower().strip()
    # Remove common MathJax/formatting wrapper tokens
    for token in [
        'begin mathsize 16px style', 'end style',
        'begin mathsize 12px style',
        'begin inline style', 'end inline style',
        'begin display style', 'end display style',
    ]:
        t = t.replace(token, '')
    # Remove 'space' tokens (used as spacers in alt text)
    t = t.replace(' space ', ' ').replace(' space', ' ').replace('space ', ' ')
    # Remove 'straight' prefix (used before letter variables like straight pi)
    t = t.replace('straight ', '')
    # Remove common word-level noise
    for token in ['blank', 'presubscript', 'presuperscript']:
        t = t.replace(token, '')
    # Normalise whitespace
    t = re.sub(r'\s+', '', t)
    # Convert word-forms to symbols
    replacements = {
        'degree': '°',
        'plus': '+',
        'minus': '-',
        'times': '×',
        'dividedby': '÷',
        'lessthan': '<',
        'greaterthan': '>',
        'greaterorequalthan': '≥',
        'lessorequalthan': '≤',
        'equals': '=',
        'notequalto': '≠',
        'approximatelyequalto': '≈',
    }
    for word, sym in replacements.items():
        t = t.replace(word, sym)
    return t


def normalize_plain_text(text):
    """Normalize plain text for matching against alt text."""
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r'\s+', '', t)
    # Convert word-forms to symbols (same as alt text)
    replacements = {
        'degree': '°', 'plus': '+', 'minus': '-', 'times': '×',
        'equals': '=', 'lessthan': '<', 'greaterthan': '>',
    }
    for word, sym in replacements.items():
        t = t.replace(word, sym)
    return t


def normalize_option_text(text):
    """Normalize option display text for matching."""
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r'\s+', '', t)
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


async def extract_explanation(page):
    """Click 'Explain Answer' and extract the correct answer + explanation.

    Captures:
    - The first paragraph(s) of the dialog which contain the answer value
    - All math image alt texts
    - The full explanation text
    - The 'answer snippet' = the text/image content right after 'The answer is'
    """
    result = {
        "correct_answer": "",
        "correct_answer_raw": "",
        "correct_answer_raw_all": [],  # all images/text in the answer phrase
        "correct_answer_plain": "",    # plain-text answer if stated as text
        "correct_answer_all_images": [],
        "explanation": "",
        "explanation_images": [],
        "answer_phrase_html": "",     # raw HTML of the answer phrase
    }

    # Ensure no dialogs are blocking
    await dismiss_dialogs(page)

    explain_btn = await page.query_selector("button:has-text('Explain Answer')")
    if not explain_btn or not await explain_btn.is_visible():
        return result

    # Remove any blocking overlays first (don't remove the dialog itself)
    try:
        await page.evaluate("""() => {
            document.querySelectorAll('.ui-widget-overlay').forEach(el => el.remove());
        }""")
    except:
        pass

    try:
        await explain_btn.click(timeout=10000)
    except:
        # If overlay was blocking, force click
        try:
            await explain_btn.click(force=True, timeout=5000)
        except:
            return result
    await asyncio.sleep(3)

    # Get the solution dialog
    dialog = await page.query_selector("#abe-solutionDialog")
    if not dialog:
        dialog = await page.query_selector(".ui-dialog-content")

    if dialog:
        # Extract the answer phrase HTML (the first <p> containing "The answer is")
        answer_phrase_data = await dialog.evaluate("""el => {
            const paragraphs = el.querySelectorAll('p, span');
            for (const p of paragraphs) {
                const text = p.innerText || p.textContent || '';
                if (text.toLowerCase().includes('the answer is')) {
                    return {
                        html: p.innerHTML.substring(0, 3000),
                        text: p.innerText.substring(0, 1000)
                    };
                }
            }
            // Fallback: return first 500 chars of dialog HTML
            return {
                html: el.innerHTML.substring(0, 3000),
                text: el.innerText.substring(0, 500)
            };
        }""")

        result["answer_phrase_html"] = answer_phrase_data.get("html", "")
        answer_text = answer_phrase_data.get("text", "")

        # Get all images with alt text from the answer phrase specifically
        # Parse the answer phrase HTML to find images within it
        answer_phrase_imgs = []
        if answer_phrase_data.get("html"):
            # Use page.evaluate to get images from the phrase
            answer_imgs_alt = await dialog.evaluate("""el => {
                const allP = el.querySelectorAll('p, span');
                for (const p of allP) {
                    const text = (p.innerText || '').toLowerCase();
                    if (text.includes('the answer is')) {
                        const imgs = p.querySelectorAll('img');
                        return Array.from(imgs).map(img => img.getAttribute('alt') || '');
                    }
                }
                // Fallback: first 3 images in dialog
                const imgs = el.querySelectorAll('img');
                return Array.from(imgs).slice(0, 3).map(img => img.getAttribute('alt') || '');
            }""")
            answer_phrase_imgs = [a for a in answer_imgs_alt if a]

        # Get ALL images from the dialog
        all_imgs = await dialog.query_selector_all("img")
        all_alt_texts = []
        for img in all_imgs:
            alt = await img.get_attribute("alt")
            if alt:
                all_alt_texts.append(alt)

        result["explanation_images"] = all_alt_texts
        result["correct_answer_all_images"] = all_alt_texts

        # Set correct_answer_raw from answer phrase images (preferred) or first dialog image
        if answer_phrase_imgs:
            result["correct_answer_raw"] = answer_phrase_imgs[0]
            result["correct_answer_raw_all"] = answer_phrase_imgs
        elif all_alt_texts:
            result["correct_answer_raw"] = all_alt_texts[0]
            result["correct_answer_raw_all"] = [all_alt_texts[0]]

        # Extract plain-text answer from "The answer is X" pattern
        # This catches answers like "The answer is 22.5°" or "The answer is yellow"
        # Match to end of line (not period, to handle decimal numbers like 22.5)
        plain_match = re.search(
            r'The answer is:?\s*(.+?)(?:\n|$)',
            answer_text,
            re.DOTALL
        )
        if plain_match:
            plain_answer = plain_match.group(1).strip()
            # Strip trailing period if present (but keep decimal points)
            if plain_answer.endswith('.') and not plain_answer[-2:-1].isdigit():
                plain_answer = plain_answer[:-1].strip()
            # Also strip trailing units like 'cm', 'cm2', 'm/s' for matching purposes
            # but keep the original too
            if plain_answer and len(plain_answer) > 0:
                result["correct_answer_plain"] = plain_answer

        # Extract explanation text
        full_text = await dialog.inner_text()
        lines = full_text.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped in ("Solution", "Close", ""):
                continue
            cleaned_lines.append(stripped)

        result["explanation"] = "\n".join(cleaned_lines)

        # Try to find a direct letter answer in the text
        answer_match = re.search(r'The answer is:?\s*([A-E])\b', full_text)
        if answer_match:
            result["correct_answer"] = answer_match.group(1)

    # Close dialog properly using the Close button
    closed = await dismiss_dialogs(page)
    if not closed:
        # Fallback: remove overlay via JS but DON'T remove the dialog itself
        # (removing the dialog breaks the player's internal state)
        try:
            await page.evaluate("""() => {
                document.querySelectorAll('.ui-widget-overlay').forEach(el => el.remove());
            }""")
            await asyncio.sleep(0.5)
        except:
            pass

    return result


def match_answer_to_option(correct_raw, options, correct_plain="", explanation_text=""):
    """Match the raw correct answer to an option letter using multiple strategies.

    Strategies (in order):
    1. Normalized alt-text exact match (removes formatting tokens)
    2. Normalized alt-text substring match
    3. Plain-text answer matched to option plain text
    4. Plain-text answer matched to option math alt text (after normalization)
    5. Option values found in explanation text (for questions without explicit answer)
    6. Multi-image answer matching (join all answer-phrase images)
    """
    if not options:
        return ""

    # Strategy 1 & 2: Match correct_raw against option math_alt with normalization
    if correct_raw:
        correct_norm = normalize_alt_text(correct_raw)
        if correct_norm:
            for letter, opt_data in options.items():
                if not isinstance(opt_data, dict):
                    continue
                for alt in opt_data.get("math_alt", []):
                    alt_norm = normalize_alt_text(alt)
                    if not alt_norm:
                        continue
                    # Exact normalized match
                    if alt_norm == correct_norm:
                        return letter
                    # Substring match (one contains the other)
                    min_len = min(len(alt_norm), len(correct_norm))
                    if min_len > 8:
                        if alt_norm in correct_norm or correct_norm in alt_norm:
                            return letter

            # Strategy 6: Try joining all answer-phrase images
            # (some answers are split across multiple images)

    # Strategy 3: Match plain-text answer to option plain text
    if correct_plain:
        plain_norm = normalize_plain_text(correct_plain).rstrip('.')
        if plain_norm and len(plain_norm) >= 1:
            for letter, opt_data in options.items():
                if not isinstance(opt_data, dict):
                    continue
                opt_plain = opt_data.get("plain_text", "")
                opt_plain_norm = normalize_plain_text(opt_plain)
                if not opt_plain_norm:
                    continue
                # Exact match
                if opt_plain_norm == plain_norm:
                    return letter
                # Numeric match: extract numbers and compare as floats
                plain_num_str = re.sub(r'[^0-9.\-]', '', plain_norm)
                opt_num_str = re.sub(r'[^0-9.\-]', '', opt_plain_norm)
                if plain_num_str and opt_num_str:
                    try:
                        if float(plain_num_str) == float(opt_num_str):
                            return letter
                    except ValueError:
                        pass
                # Substring match (either direction) with relaxed length
                if len(plain_norm) >= 1 and len(opt_plain_norm) >= 1:
                    if plain_norm in opt_plain_norm or opt_plain_norm in plain_norm:
                        # But avoid trivial matches like '3' in '30'
                        if len(opt_plain_norm) >= 2 or opt_plain_norm == plain_norm:
                            return letter

    # Strategy 4: Match plain-text answer to option math alt text
    if correct_plain:
        plain_norm = normalize_plain_text(correct_plain).rstrip('.')
        # Also try a version with degree symbol converted back
        plain_for_alt = plain_norm.replace('°', 'degree')
        if plain_norm and len(plain_norm) >= 1:
            for letter, opt_data in options.items():
                if not isinstance(opt_data, dict):
                    continue
                for alt in opt_data.get("math_alt", []):
                    alt_norm = normalize_alt_text(alt)
                    if not alt_norm:
                        continue
                    if alt_norm == plain_norm or alt_norm == plain_for_alt:
                        return letter
                    if len(plain_norm) >= 2 and len(alt_norm) >= 2:
                        if plain_norm in alt_norm or alt_norm in plain_norm:
                            return letter
                        if plain_for_alt in alt_norm or alt_norm in plain_for_alt:
                            return letter

    # Strategy 5: Find option values in explanation text
    # For explanations that don't state the answer explicitly,
    # the correct option value often appears in the worked solution.
    # CAUTION: Only use this for longer values to avoid false positives.
    if explanation_text:
        expl_norm = normalize_plain_text(explanation_text)
        expl_alt_norm = normalize_alt_text(explanation_text)
        matches = []  # (letter, match_len)
        for letter, opt_data in options.items():
            if not isinstance(opt_data, dict):
                continue
            opt_matched = False
            # Check math alt text (require length >= 10 for safety)
            for alt in opt_data.get("math_alt", []):
                alt_norm = normalize_alt_text(alt)
                if alt_norm and len(alt_norm) >= 10:
                    if alt_norm in expl_norm or alt_norm in expl_alt_norm:
                        matches.append((letter, len(alt_norm)))
                        opt_matched = True
                        break
            if opt_matched:
                continue
            # Check plain text (require length >= 3 for safety)
            opt_plain = opt_data.get("plain_text", "")
            opt_plain_norm = normalize_option_text(opt_plain)
            if opt_plain_norm and len(opt_plain_norm) >= 3:
                # Use word-boundary search
                pattern = re.compile(r'(?<![0-9.])' + re.escape(opt_plain_norm) + r'(?![0-9.])')
                if pattern.search(expl_norm):
                    matches.append((letter, len(opt_plain_norm)))
        # Only accept if exactly one option matched (unique)
        if len(matches) == 1:
            return matches[0][0]
        elif len(matches) > 1:
            # Multiple matches: take the longest (most specific)
            matches.sort(key=lambda x: -x[1])
            # Only accept if best is significantly longer than second best
            if len(matches) == 1 or matches[0][1] > matches[1][1] * 1.5:
                return matches[0][0]

    return ""


async def navigate_to_first_question(page):
    """Navigate past NDA and instructions to the first question."""
    for i in range(5):
        next_btn = await page.query_selector("button:has-text('Next')")
        if next_btn and await next_btn.is_visible():
            await next_btn.click()
            await asyncio.sleep(3)
            q_num, q_total = await get_question_number(page)
            if q_num is not None:
                return q_num, q_total
    return None, None


async def extract_question_screenshot(page, module, qnum):
    """Take a screenshot of the current question."""
    screenshots_dir = SCREENSHOTS_DIR / module
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    filename = f"q{qnum:02d}.png"
    filepath = screenshots_dir / filename

    await page.screenshot(path=str(filepath), full_page=False)
    return f"esat_screenshots/{module}/{filename}"


async def check_answer_key(page):
    """Try to detect the correct answer from the answer key labels."""
    labels = await page.query_selector_all(".abe-displayAnswerKeyLabel")
    for i, label in enumerate(labels):
        text = await label.inner_text()
        if text.strip():
            return chr(65 + i)
    return ""


def derive_answer_from_text_v2(explanation, options_detailed, explanation_data, flat_options):
    """Enhanced text matching for correct answer from explanation.
    Handles patterns missed by the original matching logic."""
    
    if not explanation:
        return ""
    
    expl_lower = explanation.lower()
    options = flat_options
    
    # Pattern 1: "The answer is option X"
    m = re.search(r'the answer is option\s+([a-h])\b', expl_lower)
    if m:
        letter = m.group(1).upper()
        if letter in options:
            return letter
    
    # Pattern 2: "The answer is X." where X is a single letter at end of sentence
    # Must not match articles
    m = re.search(r'the answer is:?\s+([a-h])\s*[\.\;\n\r]', expl_lower)
    if m:
        letter = m.group(1).upper()
        if letter in options:
            return letter
    
    # Pattern 2b: "The answer is row X"
    m = re.search(r'the (?:correct )?answer is row\s+([a-h])\b', expl_lower)
    if m:
        letter = m.group(1).upper()
        if letter in options:
            return letter
    
    # Pattern 2c: "In case X" for letter-only options
    if all(len(v.strip()) <= 2 for v in options.values()):
        case_matches = re.findall(r'(?:in |for )?case\s+([a-h])\b', expl_lower)
        if case_matches:
            for case_letter in case_matches:
                idx = expl_lower.find(f'case {case_letter}')
                context = expl_lower[max(0,idx-50):idx+200]
                if any(kw in context for kw in ['same', 'correct', 'no change', 'does not change', 'equal']):
                    if case_letter.upper() in options:
                        return case_letter.upper()
            unique_cases = list(dict.fromkeys(case_matches))
            if len(unique_cases) == 1:
                return unique_cases[0].upper()
    
    # Pattern 3: "The answer is: [exact option text]" — exact match
    m = re.search(r'the (?:correct )?answer is:?\s*(.+?)(?:\.|$)', explanation, re.IGNORECASE | re.MULTILINE)
    if m:
        answer_text = m.group(1).strip().rstrip('.')
        answer_norm = normalize_aggressive(answer_text)
        if answer_norm and len(answer_norm) >= 2:
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if opt_norm and opt_norm == answer_norm:
                    return letter
    
    # Pattern 4: "option X" in correct_answer_plain
    correct_plain = explanation_data.get("correct_answer_plain", "")
    if correct_plain:
        m = re.match(r'option\s+([a-h])\b', correct_plain, re.IGNORECASE)
        if m:
            letter = m.group(1).upper()
            if letter in options:
                return letter
    
    # Pattern 5: Variable matching
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
            return letter
    
    # Pattern 6: Token matching for statement-combo options
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
                        return letter
                    if 'none' in answer_lower and 'none' in opt_text.lower():
                        return letter
    
    # Pattern 7: Sentence matching
    m = re.search(r'(?:so |thus |therefore |and so )?(?:the )?(?:correct )?answer is\s+(.+?)(?:\.|,|$)', explanation, re.IGNORECASE | re.MULTILINE)
    if m:
        answer_text = m.group(1).strip().rstrip('.,')
        answer_norm = normalize_aggressive(answer_text)
        if answer_norm:
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if opt_norm and opt_norm == answer_norm:
                    return letter
    
    # Pattern 8: Numeric matching with sign awareness
    correct_raw = explanation_data.get("correct_answer_raw", "")
    correct_images = explanation_data.get("correct_answer_all_images", [])
    all_imgs = []
    if correct_raw:
        all_imgs.append(correct_raw)
    if correct_images:
        all_imgs.extend(correct_images[:3])
    for img_text in all_imgs:
        img_norm = normalize_alt_text(img_text)
        if not img_norm or len(img_norm) < 3:
            continue
        for letter, opt_data in options_detailed.items():
            if not isinstance(opt_data, dict):
                continue
            for alt in opt_data.get("math_alt", []):
                alt_norm = normalize_alt_text(alt)
                if not alt_norm:
                    continue
                if alt_norm == img_norm:
                    return letter
                min_len = min(len(alt_norm), len(img_norm))
                if min_len >= 4:
                    if alt_norm in img_norm or img_norm in alt_norm:
                        return letter
    
    # Pattern 9: "The answer is [number]"
    m = re.search(r'the answer is:?\s+(\d+\.?\d*)', expl_lower)
    if m:
        try:
            answer_num = float(m.group(1))
            for letter, opt_text in options.items():
                opt_d = options_detailed.get(letter, {})
                opt_plain = opt_d.get("plain_text", "") if isinstance(opt_d, dict) else ""
                search_text = opt_plain or opt_text
                opt_nums = re.findall(r'(\d+\.?\d*)', search_text)
                for opt_num_str in opt_nums:
                    try:
                        if float(opt_num_str) == answer_num:
                            return letter
                    except ValueError:
                        pass
        except ValueError:
            pass
    
    # Pattern 10: "It is not possible that: [option text]"
    m = re.search(r'it is not possible that:?\s*(.+?)(?:\.|\n|$)', expl_lower)
    if m:
        negated_text = m.group(1).strip().rstrip('.')
        neg_norm = normalize_aggressive(negated_text)
        if neg_norm and len(neg_norm) >= 5:
            for letter, opt_text in options.items():
                opt_norm = normalize_aggressive(opt_text)
                if opt_norm and opt_norm == neg_norm:
                    return letter
                if len(opt_norm) >= 10 and len(neg_norm) >= 10:
                    if opt_norm in neg_norm or neg_norm in opt_norm:
                        return letter
    
    # Pattern 11: Numeric tail extraction with sign awareness
    lines = explanation.split('\n')
    last_5 = ' '.join(lines[-5:]) if len(lines) >= 5 else explanation
    nums_tail = re.findall(r'(?:=|is|equals|gives)\s*([+\-\u2212]?)\s*(\d+\.?\d*)', last_5, re.IGNORECASE)
    if nums_tail:
        for sign, num_str in reversed(nums_tail):
            try:
                num = float(num_str)
                if num < 10:
                    continue  # Skip small numbers (likely not answers)
                is_pos = sign in ['+', '']
                for letter, opt_text in options.items():
                    opt_d = options_detailed.get(letter, {})
                    opt_plain = opt_d.get("plain_text", "") if isinstance(opt_d, dict) else ""
                    search_text = opt_plain or opt_text
                    opt_has_neg = '−' in search_text[:3] or search_text.strip().startswith('-')
                    opt_nums = re.findall(r'(\d+\.?\d*)', search_text)
                    for opt_num_str in opt_nums:
                        try:
                            if abs(float(opt_num_str) - num) < 0.01 * max(abs(num), 1):
                                if is_pos and opt_has_neg:
                                    continue
                                if not is_pos and not opt_has_neg:
                                    continue
                                return letter
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
                return best_match
    
    # Pattern 13: Plain text numeric matching
    if correct_plain:
        plain_num = re.search(r'(\d+\.?\d*)', correct_plain)
        if plain_num:
            try:
                pn = float(plain_num.group(1))
                for letter, opt_text in options.items():
                    opt_d = options_detailed.get(letter, {})
                    opt_plain = opt_d.get("plain_text", "") if isinstance(opt_d, dict) else ""
                    search_text = opt_plain or opt_text
                    for opt_num_str in re.findall(r'(\d+\.?\d*)', search_text):
                        try:
                            if abs(float(opt_num_str) - pn) < 0.01 * max(abs(pn), 1):
                                return letter
                        except ValueError:
                            pass
            except ValueError:
                pass
    
    return ""


# ============================================================
# Main Extraction Logic
# ============================================================

async def extract_module(module_key, browser, verbose=True):
    """Extract all questions from one ESAT module."""
    module_info = MODULES[module_key]
    url = module_info["url"]
    id_prefix = module_info["id_prefix"]

    if verbose:
        print(f"\n{'='*60}", flush=True)
        print(f"  Extracting: {module_info['label']}", flush=True)
        print(f"  URL: {url}", flush=True)
        print(f"{'='*60}", flush=True)

    context = await browser.new_context(viewport={"width": 1400, "height": 900})
    page = await context.new_page()

    questions = []

    try:
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        except:
            pass
        await asyncio.sleep(5)

        final_url = page.url
        if verbose:
            print(f"  Test player URL: {final_url}", flush=True)

        # Check for login
        if "login" in final_url.lower() or "signin" in final_url.lower():
            print(f"  ERROR: Login required!", flush=True)
            return {"error": "login_required", "questions": []}

        # Navigate to first question
        q_num, q_total = await navigate_to_first_question(page)
        if q_num is None:
            print(f"  ERROR: Could not reach first question", flush=True)
            return {"error": "navigation_failed", "questions": []}

        if verbose:
            print(f"  Total questions: {q_total}", flush=True)

        current_q = q_num
        last_q = None
        repeat_count = 0

        while current_q is not None:
            # Ensure no leftover dialogs from previous question
            await dismiss_dialogs(page)

            # Scroll through the question to satisfy 'viewed entire screen' requirement
            await scroll_question_into_view(page)

            # Select answer A to avoid any "no answer selected" prompts when navigating
            try:
                radio = await page.query_selector("#abe-contentPane input[type='radio'][value='A']")
                if radio:
                    await radio.click(timeout=3000)
                    await asyncio.sleep(0.5)
            except:
                pass

            # Loop protection: if we see the same question 3 times, skip
            if current_q == last_q:
                repeat_count += 1
                if repeat_count >= 3:
                    if verbose:
                        print(f"    WARNING: Stuck on Q{current_q}, skipping...", flush=True)
                    # Try Navigator to jump to next question
                    nav_btn = await page.query_selector("button:has-text('Navigator')")
                    if nav_btn and await nav_btn.is_visible():
                        await nav_btn.click()
                        await asyncio.sleep(2)
                        next_q_btn = await page.query_selector(f"button:has-text('{current_q + 1}')")
                        if next_q_btn:
                            await next_q_btn.click()
                            await asyncio.sleep(2)
                            repeat_count = 0
                            current_q, _ = await get_question_number(page)
                            last_q = current_q
                            continue
                    break
            else:
                repeat_count = 0
            last_q = current_q
            if verbose:
                print(f"\n  --- Question {current_q} of {q_total} ---", flush=True)

            # Extract question text
            q_text, q_images = await extract_question_text(page)

            # Extract options
            options = await extract_options(page)

            # Screenshot
            screenshot_path = await extract_question_screenshot(page, module_key, current_q)

            # Extract explanation
            explanation_data = await extract_explanation(page)

            # After explanation dialog, scroll question again to satisfy view requirement
            await scroll_question_into_view(page)

            # Determine correct answer using multiple strategies
            correct_answer = explanation_data.get("correct_answer", "")

            if not correct_answer:
                correct_answer = match_answer_to_option(
                    explanation_data.get("correct_answer_raw", ""),
                    options,
                    correct_plain=explanation_data.get("correct_answer_plain", ""),
                    explanation_text=explanation_data.get("explanation", "")
                )

            if not correct_answer:
                correct_answer = await check_answer_key(page)

            # If still no answer, try matching all answer-phrase images as a joined string
            if not correct_answer:
                all_raw = explanation_data.get("correct_answer_raw_all", [])
                if len(all_raw) > 1:
                    joined = " ".join(all_raw)
                    correct_answer = match_answer_to_option(
                        joined, options,
                        correct_plain=explanation_data.get("correct_answer_plain", ""),
                        explanation_text=""
                    )
            
            # Strategy 7: Cross-check ALL explanation images against option alt texts
            if not correct_answer:
                all_expl_imgs = explanation_data.get("explanation_images", [])
                if all_expl_imgs:
                    matches = []
                    for img_alt in all_expl_imgs:
                        img_norm = normalize_alt_text(img_alt)
                        if not img_norm or len(img_norm) < 5:
                            continue
                        for letter, opt_data in options.items():
                            if not isinstance(opt_data, dict):
                                continue
                            for opt_alt in opt_data.get("math_alt", []):
                                opt_norm = normalize_alt_text(opt_alt)
                                if not opt_norm:
                                    continue
                                if img_norm == opt_norm:
                                    matches.append(letter)
                                elif len(img_norm) > 6 and len(opt_norm) > 5:
                                    if img_norm in opt_norm or opt_norm in img_norm:
                                        matches.append(letter)
                    unique_matches = list(set(matches))
                    if len(unique_matches) == 1:
                        correct_answer = unique_matches[0]
            
            # Strategy 8: Enhanced explanation text matching (v2)
            if not correct_answer and explanation_data.get("explanation"):
                correct_answer = derive_answer_from_text_v2(
                    explanation_data["explanation"],
                    options,
                    explanation_data,
                    flat_options
                )

            # Flatten options for JSON output
            flat_options = {}
            for letter, opt_data in options.items():
                if isinstance(opt_data, dict):
                    flat_options[letter] = opt_data.get("text", "needs_manual_transcription")
                else:
                    flat_options[letter] = opt_data

            question = {
                "id": f"{id_prefix}-Q{current_q}",
                "year": "specimen",
                "paper": "ESAT",
                "module": module_key,
                "question_number": current_q,
                "question_text": q_text,
                "question_images": q_images,
                "screenshot": screenshot_path,
                "explanation_screenshot": "",
                "options": flat_options,
                "options_detailed": options,
                "correct_answer": correct_answer,
                "correct_answer_raw": explanation_data.get("correct_answer_raw", ""),
                "correct_answer_plain": explanation_data.get("correct_answer_plain", ""),
                "correct_answer_images": explanation_data.get("correct_answer_all_images", []),
                "explanation": explanation_data.get("explanation", ""),
                "explanation_images": explanation_data.get("explanation_images", []),
                "extracted_at": datetime.now().isoformat(),
            }

            questions.append(question)

            if verbose:
                print(f"    Text: {q_text[:100]}...", flush=True)
                print(f"    Options: {list(options.keys())}", flush=True)
                print(f"    Correct: {correct_answer or '(matching needed)'}", flush=True)
                print(f"    Explanation: {question['explanation'][:80]}...", flush=True)
                print(f"    Screenshot: {screenshot_path}", flush=True)

            # Next question
            if current_q >= q_total:
                break

            next_clicked = await click_next(page)

            if not next_clicked:
                # Use Navigator to jump to next question
                next_clicked = await navigate_via_navigator(page, current_q + 1)

            if not next_clicked:
                break

            new_q, _ = await get_question_number(page)

            # If still on same question after Next, try Navigator
            if new_q == current_q or new_q is None:
                nav_ok = await navigate_via_navigator(page, current_q + 1)
                if nav_ok:
                    new_q, _ = await get_question_number(page)

                if new_q == current_q or new_q is None:
                    if verbose:
                        print(f"    WARNING: Cannot advance past Q{current_q}, stopping", flush=True)
                    break

            current_q = new_q

    except Exception as e:
        print(f"  ERROR during extraction: {e}", flush=True)
        import traceback
        traceback.print_exc()

    finally:
        await context.close()

    return {
        "module": module_key,
        "label": module_info["label"],
        "total_questions": len(questions),
        "questions": questions,
        "extracted_at": datetime.now().isoformat(),
    }


async def main():
    parser = argparse.ArgumentParser(description="ESAT Specimen Test Extractor")
    parser.add_argument("--module", default="maths1",
                       help="Module to extract (maths1, maths2, physics, chemistry, biology, or 'all')")
    parser.add_argument("--output-dir", default=str(JSON_DIR),
                       help="Output directory for JSON")
    parser.add_argument("--verbose", action="store_true", default=True)
    args = parser.parse_args()

    JSON_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.module.lower() == "all":
        modules_to_run = list(MODULES.keys())
    elif args.module.lower() == "list":
        print("\nAvailable ESAT specimen modules:")
        for key, info in MODULES.items():
            print(f"  {key}: {info['label']}")
        return
    else:
        modules_to_run = [args.module.lower()]

    for m in modules_to_run:
        if m not in MODULES:
            print(f"ERROR: Unknown module '{m}'. Available: {', '.join(MODULES.keys())}")
            return

    print(f"\nESAT Specimen Test Extraction System", flush=True)
    print(f"====================================", flush=True)
    print(f"Modules: {', '.join(modules_to_run)}", flush=True)
    print(f"Output: {args.output_dir}", flush=True)
    print(f"Date: {datetime.now().isoformat()}", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        all_results = {}

        for module_key in modules_to_run:
            result = await extract_module(module_key, browser, args.verbose)
            all_results[module_key] = result

            # Save per-module JSON
            output_file = Path(args.output_dir) / f"esat_specimen_{module_key}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n  Saved JSON: {output_file}", flush=True)
            print(f"  Questions extracted: {len(result.get('questions', []))}", flush=True)

        await browser.close()

        # Save combined JSON
        combined_file = Path(args.output_dir) / "esat_specimen_all.json"
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\nCombined JSON saved: {combined_file}", flush=True)

        # Summary
        print(f"\n{'='*60}", flush=True)
        print(f"  EXTRACTION SUMMARY", flush=True)
        print(f"{'='*60}", flush=True)
        for module_key in modules_to_run:
            result = all_results[module_key]
            q_count = len(result.get("questions", []))
            has_answer = sum(1 for q in result.get("questions", []) if q.get("correct_answer"))
            has_explanation = sum(1 for q in result.get("questions", []) if q.get("explanation"))
            needs_manual = sum(1 for q in result.get("questions", []) if q.get("question_text") == "needs_manual_transcription")
            print(f"  {module_key}: {q_count} questions | {has_answer} with answers | {has_explanation} with explanations | {needs_manual} need manual text", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
