# OCR Quality Audit Report

**Date:** 2026-07-09  
**Scope:** Full corpus — 48 paper files, 1,687 questions  
**Corpus path:** `/home/ubuntu/.paperclip/esat-shared/corpus/json/`

---

## Executive Summary

The OCR extraction pipeline (`extract_papers.py` using `pdftotext -layout`) produces **systematically garbled mathematical notation** in question text and options across 82.9% of questions (1,399 out of 1,687). The core problem is that spatial math — fractions, powers, multi-line expressions, square roots, integrals — is flattened into linear text, losing structural information.

**ESAT specimen papers are an exception:** they were extracted using a different pipeline (likely Claude/GPT-4o vision model) and have proper LaTeX formatting in both question text and options. This demonstrates the target quality level and the feasibility of a vision-model fix.

**Recommended approach:** Vision-model re-transcription using Claude 3.5 Sonnet or GPT-4o to read each question from the original PDF pages and produce LaTeX-formatted output. Estimated cost: $100–170 for the full corpus. This is the same approach that produced the high-quality ESAT extractions.

---

## Detailed Findings

### 1. Problem Scope by Paper Type

| Paper Type | Questions | Affected | % Affected | Primary Issues |
|---|---|---|---|---|
| **ENGAA S1** | 362 | 339 | 93.6% | Broken fractions, unicode math, multiline flattening, orphaned options |
| **NSAA S1** | 680 | 653 | 96.0% | Same as ENGAA (same extraction pipeline) |
| **TMUA** | 300 | 278 | 92.7% | Same + superscripts, unbalanced brackets |
| **NSAA S2** | 210 | 75 | 35.7% | Unicode math in options only (text extraction is better for S2) |
| **ESAT specimen** | 135 | 54 | 40.0% | Minor: garbled bytes in biology, unicode in science options |
| **TOTAL** | **1,687** | **1,399** | **82.9%** | |

### 2. Issue Categories

#### Category A: Broken Fractions (HIGH SEVERITY)
**~40% of ENGAA/NSAA S1/TMUA questions**

Fractions rendered spatially in PDFs (numerator over denominator with a horizontal bar) are split across lines by `pdftotext`. The numerator appears on one line, the denominator on the next, with the spatial relationship completely lost.

**Example — ENGAA 2016 Q1:**
- **Original:** `(x/2) − 8 < 6 − (2/x)`
- **Extracted:** `x Find the complete set of solutions to − 8 < 6 − 2`
- **Raw text shows:** `x` on one line, `Find the complete set of solutions to − 8 < 6 −` on next, `2` alone on the following line
- The fraction `x/2` at the start becomes an orphaned `x`, and `2/x` at the end becomes an orphaned `2`

**Example — ENGAA 2022 Q1:**
- **Original:** A complex fraction expression involving `y³/(3xz²)` raised to various powers
- **Extracted:** `1 Which one of the following is a simplification of 2 ⁪ ³⁄₂ ⁪ ᵞ ³ˣᶻ ʸ³ ʸ ᵞ⁄₃ ᵞ ᵞ`
- Options are similarly garbled: `'y4 3 xz 2'`, `'y5'`, etc.

#### Category B: Multiline Flattening (HIGH SEVERITY)
**~85% of ENGAA/NSAA S1/TMUA questions**

Multi-line mathematical expressions (equations spanning multiple lines, systems of equations, long expressions) are concatenated into a single line, losing line breaks that convey mathematical structure.

- **ENGAA S1:** 310 questions affected
- **NSAA S1:** 628 questions affected
- **TMUA:** 240 questions affected

#### Category C: Unicode Math Symbols Instead of LaTeX (MEDIUM SEVERITY)
**~30–35% of questions across all paper types**

Mathematical symbols extracted as unicode characters rather than LaTeX:
- `−` (minus) instead of `−` or `-`
- `≤`, `≥`, `≠`, `≈` instead of `\le`, `\ge`, `\ne`, `\approx`
- `√` instead of `\sqrt{}`
- `°` instead of `^\circ`
- `²`, `³` instead of `^{2}`, `^{3}` (superscript unicode chars)
- `₀`, `₁` instead of `_{0}`, `_{1}` (subscript unicode chars)
- `×` instead of `\times`
- `÷` instead of `\div`
- `π` instead of `\pi`

This also appears in **options text** across all paper types (hundreds of option entries).

#### Category D: Orphaned/Tiny Options (MEDIUM SEVERITY)
**Hundreds of option entries across all paper types**

Options that are just a number (e.g., `'2'`, `'3'`, `'0'`) or a very short expression (e.g., `'8π'`, `'√2'`, `'2R'`). Many of these are correct answers that happen to be simple values, but some are broken fractions where only the denominator survived.

- **TINY_OPT:** Option text is 1-2 characters (hundreds of instances)
- **LONE_EXPR_OPT:** Option is just a number that could be a broken expression

#### Category E: Garbled Bytes (MEDIUM SEVERITY)
**ESAT biology primarily (17 questions), some chemistry/physics**

Some ESAT science questions have garbled byte sequences — likely from embedded fonts or special characters that pdftotext couldn't decode. These may have been extracted from scanned pages or pages with unusual font encoding.

#### Category F: Unbalanced Brackets (LOW SEVERITY)
**Isolated instances**

Parentheses or brackets that don't balance, usually caused by a closing bracket being on the "denominator line" of a fraction and getting lost.

#### Category G: Minor — Orphaned Variable at Question Start (LOW SEVERITY)
**~1-5 instances**

Question text starts with a lone variable (e.g., `"x Find the..."`) — this is the numerator of a fraction that was the first element of the question.

### 3. Paper Type Deep Dive

#### ENGAA (8 papers, 2016–2023, 362 questions)
- **Most affected:** 2022 S1 — 100% of questions have issues
- **Least affected:** 2020 S1 — 90% (still very high)
- **Consistent pattern:** Every year has ~90-96% questions affected
- **Issue mix:** Broken fractions dominate, followed by unicode math, orphaned options
- The `raw_text` field preserves more spatial info and could help a repair pipeline

#### TMUA (16 papers, 2017–2023 + specimen, 300 questions)
- **Most affected:** 2019 P1, 2020 P2, 2021 P1 — 100%
- **Least affected:** 2017 P2, 2019 P2 — 85%
- **Additional issues:** More superscript/subscript chars than ENGAA (12 instances vs 3)
- **One unbalanced brackets case** in 2017 P2
- Options frequently have trailing numbers from fraction denominators (e.g., `'50 8'` where `8` is from a `3/8` fraction)

#### NSAA S1 (8 papers, 2016–2023, 680 questions)
- **Most affected:** 2017 S1, 2020 S1, 2022 S1, 2023 S1 — 98%
- **Least affected:** 2016 S1 — 94%
- **Largest paper type** and most questions overall
- Some questions have garbled unicode control characters (e.g., `''`, `'⇐'` in NSAA 2017)

#### NSAA S2 (12 papers, 2020–2022 + specimen, 210 questions)
- **Significantly better** than S1 — only 35.7% affected
- Issues are primarily unicode math symbols in options (not broken fractions)
- Question text is generally readable
- S2 papers were likely processed differently or have simpler mathematical notation

#### ESAT Specimen (5 papers, 135 questions)
- **Best quality** — question text uses LaTeX formatting (e.g., `\sqrt{\frac{2}{8-\pi}}`)
- Options are properly LaTeX formatted
- Has screenshots and explanations (extracted via vision model)
- **Remaining issues:** Minor garbled bytes in biology (17Q), some unicode math in science options
- This is the **target quality level** for the full corpus

### 4. Comparison: pdftotext Pipeline vs Vision Model Pipeline

| Metric | pdftotext (ENGAA/NSAA/TMUA) | Vision Model (ESAT) |
|---|---|---|
| LaTeX fractions | ❌ Broken | ✅ `\frac{}{}` |
| LaTeX roots | ❌ Unicode `√` | ✅ `\sqrt{}` |
| LaTeX powers | ❌ Unicode `²³` or missing | ✅ `^{2}` |
| Multi-line math | ❌ Flattened | ✅ Preserved |
| Options quality | ❌ Often broken | ✅ LaTeX formatted |
| Extra metadata | ❌ None | ✅ Screenshots, explanations |
| Cost per question | ~$0 (pdftotext) | ~$0.06–0.10 |

---

## Fix Approach Recommendations

### Option 1: Vision Model Re-transcription (RECOMMENDED)

**Approach:** Use a multimodal LLM (Claude 3.5 Sonnet, GPT-4o, or Gemini 1.5 Pro) to read each question page from the original PDFs and produce LaTeX-formatted question text + options.

**Implementation:**
1. Convert each question paper PDF to page images (one image per page)
2. For each page, send the image to the vision model with a structured prompt asking for:
   - Question number
   - Question text in LaTeX format
   - All options (A–H) in LaTeX format
   - Diagram presence (yes/no)
3. Parse the model output into the existing JSON schema
4. Merge with existing metadata (correct answers from answer keys)

**Model options:**
| Model | Quality | Cost/question* | Speed | Recommendation |
|---|---|---|---|---|
| Claude 3.5 Sonnet | Excellent for math | ~$0.06 | Medium | ✅ Best quality/price |
| GPT-4o | Good for math | ~$0.05 | Fast | Good alternative |
| Gemini 1.5 Pro | Good, cheap | ~$0.02 | Fast | Budget option |

*Estimates based on ~1000–2000 input tokens (image) + ~300 output tokens per question page. Multiple questions per page reduces per-question cost.

**Batch processing:**
- Questions are typically grouped 3–5 per page
- A single model call per page can extract all questions on that page
- ~500–600 pages across the full corpus
- Can process in parallel batches of 10–20 pages

**Cost estimate:**
- Claude 3.5 Sonnet: ~500 pages × $0.15/page (image + text) = **~$75–100**
- GPT-4o: ~500 pages × $0.10/page = **~$50–75**
- Gemini 1.5 Pro: ~500 pages × $0.05/page = **~$25–50**

**Expected quality:**
- Based on ESAT specimen results: >95% accuracy for LaTeX transcription
- Remaining 5%: edge cases with complex diagrams, multi-column layouts
- **Recommendation:** Spot-check 10% of output after batch processing

**Implementation complexity:** Medium
- Need to: render PDF pages to images, write prompt templates, parse structured output, validate against answer keys
- Existing ESAT extraction code can serve as a template
- Estimated dev time: 2–3 days

### Option 2: Post-OCR LaTeX Repair (NOT RECOMMENDED as primary)

**Approach:** Send the garbled `question_text` + `raw_text` to an LLM and ask it to reconstruct the correct LaTeX.

**Problems:**
- The garbled text is **missing information** — fractions split across lines lose the `/` operator entirely
- The model would need to **guess** the original mathematical structure from context
- High hallucination risk: the model might "fix" expressions that were actually correct, or invent fractions that didn't exist
- The `raw_text` helps but still loses the visual fraction bar

**Cost estimate:**
- ~$0.005/question for text-only LLM call = **~$8–15 total**
- Much cheaper but much lower quality

**Expected quality:**
- 60–70% accurate repair (fractions are essentially unrepairable from text alone)
- High false positive rate for introducing new errors

**When useful:** As a secondary pass to fix unicode symbols (replacing `√` with `\sqrt{}`, `²` with `^{2}`) for the ~35% of questions that only have formatting issues, not structural damage.

### Option 3: Hybrid (RECOMMENDED with Option 1)

**Approach:**
1. **Phase 1:** Vision model re-transcription for all ENGAA S1, NSAA S1, TMUA questions (1,342 questions)
2. **Phase 2:** LLM text repair for NSAA S2 and ESAT science questions that have minor unicode issues (75 NSAA S2 + ~30 ESAT = ~105 questions)
3. **Phase 3:** Manual review of any questions where the vision model output doesn't match the expected answer key

**Cost estimate:**
- Phase 1: ~$75–100 (vision model)
- Phase 2: ~$1–2 (text-only LLM)
- Phase 3: Manual review of ~50–100 edge cases (human time: ~2–3 hours)
- **Total: ~$80–110**

---

## Recommended Implementation Plan

### Step 1: Build the vision transcription pipeline
Write a script that:
1. Opens each question paper PDF with pymupdf
2. Renders each page to a high-res PNG (300 DPI)
3. Sends the page image to Claude 3.5 Sonnet with a structured prompt
4. Parses the JSON output into the existing corpus schema
5. Preserves existing `correct_answer` from answer keys

### Step 2: Prompt Template (for Claude 3.5 Sonnet)

```
You are a specialist in transcribing mathematics exam questions into structured JSON 
with LaTeX notation.

Look at this page from a Cambridge admissions test paper. Extract ALL multiple-choice 
questions visible on this page.

For each question, produce:
- question_number: The question number
- question_text: The full question text with ALL mathematical notation in LaTeX format
- options: A dict of option letter -> option text, ALL in LaTeX format
- has_diagram: true if the question includes a graph, diagram, or figure

LaTeX formatting rules:
- Fractions: use \frac{numerator}{denominator}
- Square roots: use \sqrt{...}
- Powers: use ^{...}
- Subscripts: use _{...}
- Greek letters: use \pi, \theta, \alpha, etc.
- Inequalities: use \le, \ge, \ne, <, >
- Multiplication: use \times
- Division: use \frac or \div
- Vectors: use \vec{...}
- Integrals: use \int
- Summations: use \sum
- Degrees: use ^\circ
- Set notation: use \in, \subset, \cup, \cap, etc.

Output valid JSON only, no markdown fences:
{
  "questions": [
    {
      "question_number": 1,
      "question_text": "...",
      "options": {"A": "...", "B": "...", ...},
      "has_diagram": false
    }
  ]
}
```

### Step 3: Validation
For each transcribed question:
1. Check that `question_text` is non-empty and >20 characters
2. Check that all expected options (A–H as applicable) are present
3. Verify `correct_answer` still matches an option key
4. Flag any questions with `\frac{` in options but not in question text (possible missed fraction)
5. Spot-check 10% against original PDFs

### Step 4: Phase 2 — Minor repairs
For NSAA S2 and ESAT science questions with only unicode issues, run a text-only LLM pass to:
- Replace `√` → `\sqrt{...}` (needs context to determine what's under the root)
- Replace `²` → `^{2}`, `³` → `^{3}`
- Replace `π` → `\pi`, `θ` → `\theta`, etc.
- Replace `≤` → `\le`, `≥` → `\ge`
- These are safe replacements with low hallucination risk

### Step 5: Backup and replace
1. Backup existing JSON files (`.json` → `.json.bak`) — already done for some
2. Write new JSON files with the corrected data
3. Update `extraction-summary.json`
4. Re-run any downstream enrichment pipelines

---

## Priority Order

1. **ENGAA and TMUA first** — these are the math-heavy papers most affected
2. **NSAA S1 second** — largest paper type, similar issues
3. **NSAA S2 and ESAT science** — lower priority, minor issues only
4. **ESAT maths** — already good quality, skip or minor cleanup only

---

## Appendix: Key Files

| File | Purpose |
|---|---|
| `scripts/extract_papers.py` | Current extraction script (pdftotext-based) |
| `corpus/json/engaa/*.json` | ENGAA corpus (8 papers, 362Q) |
| `corpus/json/nsaa/*.json` | NSAA S1 corpus (8 papers, 680Q) |
| `corpus/json/nsaa_s2/*.json` | NSAA S2 corpus (12 papers, 210Q) |
| `corpus/json/tmua/*.json` | TMUA corpus (16 papers, 300Q) |
| `corpus/json/esat/*.json` | ESAT specimen (5 papers, 135Q) |
| `corpus/format-manifest.json` | Paper format metadata |
| `corpus/engaa/*.pdf` | Original ENGAA PDFs |
| `corpus/nsaa/*.pdf` | Original NSAA PDFs |
| `corpus/tmua/*.pdf` | Original TMUA PDFs |
| `answer-key-audit.md` | Recent answer key audit report |

---

## Appendix: Full Audit Data

Detailed per-question audit results saved to `/tmp/ocr_audit_full.json`.
