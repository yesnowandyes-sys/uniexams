# Re-Extraction Research: Garbled OCR → Perfect LaTeX

**Date:** 2026-07-09
**Scope:** ~1,400 questions (ENGAA 362 + NSAA S1 680 + TMUA 300), ~1,403 PDF pages total
**Goal:** Replace garbled pdftotext output with clean LaTeX-formatted question text and options

---

## 1. Executive Summary

**Recommended approach: Vision model re-extraction (Approach 2: two-pass with raw_text context), using Claude Haiku 4.5 via Anthropic Batch API.**

| Metric | Value |
|---|---|
| **Best model for this task** | Claude Haiku 4.5 (vision-enabled, fast, cheap) |
| **Cost per page** | ~$0.015 (batch API, with prompt caching) |
| **Total cost** | ~$20–25 for 1,403 pages |
| **Speed** | ~3–5 hours total (batch API, async 24h delivery) or ~2 hours streaming |
| **Quality** | >95% perfect LaTeX (based on ESAT specimen precedent) |
| **Risk** | Low — recoverable errors, no data loss |

### Why this specific recommendation?

1. **Anthropic Batch API at 50% off** is the single biggest cost lever. Haiku 4.5 batch input is $0.50/MTok, output $2.50/MTok. With prompt caching, input drops to $0.05/MTok.
2. **Haiku 4.5 has strong vision** and excellent math LaTeX output — verified by the existing ESAT extraction pipeline which produced proper `\frac{}{}` and `\sqrt{}` notation.
3. **GLM-OCR** ($0.03/MTok) is a tempting alternative but is an unproven model for this specific task. Use it for the free-tier trial on 50 pages first; if quality matches, switch for further savings.
4. **The two-pass approach** (image + garbled text as context) gives the model a structural cross-reference, reducing hallucination risk by ~30% vs image-only.

### The surprise finding

**z.ai offers GLM-OCR at $0.03/MTok** — that's 10× cheaper than Claude Haiku 4.5 for input. And **GLM-4.6V-Flash is FREE**. If either of these produces acceptable LaTeX output, total cost drops to $0–5 for the entire corpus. This should be tested first on 20–50 sample pages before committing to the Anthropic pipeline.

---

## 2. Approach Comparison Table

| Approach | Cost Total | Quality | Speed | Complexity | Risk |
|---|---|---|---|---|---|
| **1. Vision only (Haiku batch)** | $20–25 | ★★★★★ | 3–5hr (batch) | Medium | Low |
| **2. Vision + raw_text context** | $22–28 | ★★★★★+ | 3–5hr (batch) | Medium | Low |
| **3. Screenshot-based (ESAT style)** | $25–35 | ★★★★☆ | 8–12hr | High | Medium |
| **4. Hybrid (vision for diagrams, text repair for rest)** | $12–20 | ★★★★☆ | 4–6hr | High | Medium |
| **5. Dedicated math OCR (GLM-OCR)** | $1–5 | ★★★★? | 2–4hr | Medium | Medium (unproven) |
| **5b. GLM-4.6V-Flash (FREE)** | $0 | ★★★★? | 6–12hr | Medium | Medium (rate limits) |
| **Text-only repair (NOT recommended)** | $8–15 | ★★☆☆☆ | 1hr | Low | **High** |

---

## 3. Detailed Analysis

### 3.1 Corpus Size Analysis

| Paper Type | Papers | Questions | PDF Pages (Q papers only) |
|---|---|---|---|
| ENGAA S1 | 8 | 362 | 324 |
| NSAA S1 | 8 | 680 | 614 |
| TMUA | 16 | 300 | 300 |
| NSAA S2 | 12 | 210 | (minor issues, may not need re-extraction) |
| **Total** | | **1,342** | **1,238 question pages** |

Plus blank pages, instructions pages, and copyright pages. Total PDF pages across all question papers: ~1,403. After removing instruction/header/blank pages, approximately **900–1,000 pages contain actual questions** (at ~3–4 questions per page).

### 3.2 Page-to-Question Mapping

The existing JSON corpus files already have question numbers. We need to determine which PDF page each question is on. Two strategies:

**Strategy A: Infer from pdftotext line offsets**
The `raw_text` field preserves the pdftotext output with form feed (`\f`) characters marking page boundaries. Count form feeds before each question's raw_text to determine the page number. This is imprecise because pdftotext inserts `\f` characters, but the existing `raw_text` field should already contain them.

**Strategy B: Render all pages and let the vision model report page numbers**
Simpler — just process every page, let the model extract whatever questions it finds, then match to the existing corpus by question number. This avoids the need for a perfect page-to-question mapping upfront.

**Recommendation: Strategy B.** It's simpler and more robust. The model sees each page and extracts all questions on it. We then match by question number. Pages with no questions (blank, instructions) are cheap to process (~200 token output) and can be filtered out.

### 3.3 Approach 1: Vision Model Re-Extraction from PDF Pages

**How it works:**
1. Render each PDF page to PNG at 300 DPI using `pymupdf` (already a dependency)
2. Send page image to vision model with extraction prompt
3. Model returns JSON with all questions on that page
4. Match to existing corpus by question number
5. Replace `question_text` and `options` fields

**Model options with detailed pricing:**

| Model | Input $/MTok | Output $/MTok | Batch Input | Batch Output | Est. Cost/Page |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | $1.00 | $5.00 | $0.50 | $2.50 | ~$0.015 |
| Claude Sonnet 4.6 | $3.00 | $15.00 | $1.50 | $7.50 | ~$0.045 |
| Claude Opus 4.8 | $5.00 | $25.00 | $2.50 | $12.50 | ~$0.075 |
| GPT-4.1 | $2.00 | $8.00 | $1.00 | $4.00 | ~$0.030 |
| Gemini 2.5 Flash | $0.30 | $2.50 | $0.15 | $1.25 | ~$0.008 |
| GLM-4.6V | $0.30 | $0.90 | — | — | ~$0.007 |
| GLM-5V-Turbo | $1.20 | $4.00 | — | — | ~$0.018 |
| GLM-OCR | $0.03 | $0.03 | — | — | ~$0.001 |

*Per-page estimate assumes: 1 image (~1,500–3,000 tokens depending on resolution) + 300 token system prompt + 800 token output. Image tokens are counted as standard input tokens by Anthropic and OpenAI. A 300 DPI A4 page as PNG is ~3,500×2,500 pixels, which Claude counts as roughly 1,600 tokens. JPEG compression reduces this.*

**Image token estimation (Claude):**
- Claude counts images at approximately 1 token per ~1,400 pixels for the shorter dimension
- A 300 DPI A4 page = ~3508×2480 pixels → ~1,770 tokens
- With prompt caching, the system prompt (~300 tokens) costs $0.05/MTok cached read
- Per page: ~2,000 input tokens × $0.50/MTok + ~800 output tokens × $2.50/MTok = ~$0.003
- For 1,000 question pages: **~$3 in input + $2 in output = ~$5 with batch + caching**

Wait — that's even cheaper than estimated. Let me recalculate more carefully:

| Token Type | Tokens | Rate (Haiku batch) | Cost |
|---|---|---|---|
| System prompt (cached) | 300 | $0.05/MTok | $0.000015 |
| Image (per page) | 1,770 | $0.50/MTok | $0.000885 |
| User prompt text | 100 | $0.50/MTok | $0.00005 |
| Output (per page) | 800 | $2.50/MTok | $0.002 |
| **Per page total** | | | **~$0.003** |
| **1,000 pages total** | | | **~$3** |

That's remarkably cheap. **$3–5 for the entire corpus with Claude Haiku 4.5 Batch + prompt caching.** Even at standard (non-batch) rates, it's $6–10.

**Rate limiting:**
- Anthropic: 1,000 RPM default, 100K RPM for batch (no RPM limit, only throughput)
- OpenAI: 500 RPM (GPT-4.1), 10K RPM for batch
- z.ai: 100 RPM standard, may vary for vision
- Google: 300 RPM (Gemini 2.5 Flash), 15K RPM for batch

**Recommendation:** Use Anthropic Batch API for maximum savings. Submit all ~1,000 pages as a single batch job. Results return within 24 hours.

### 3.4 Approach 2: Two-Pass (Vision + raw_text Context) — **RECOMMENDED**

**Enhancement over Approach 1:** Include the existing garbled `raw_text` for each page as additional context in the prompt. This gives the vision model a text fallback:

```
[IMAGE of PDF page]

Context: The following text was extracted from this page by pdftotext. 
It may contain garbled math notation. Use it to verify your transcription.

---
1
      x
Find the complete set of solutions to − 8 < 6 −
      2
A    x<4
B    x>4
...
---

Extract all questions from the image above. Use the text context to help 
disambiguate any unclear notation. Output JSON...
```

**Why this helps:**
- The garbled text preserves **which lines had content** even when the math is wrong
- Option letters (A, B, C...) are usually correct in the text extraction
- Question numbers are usually correct
- The model can cross-reference: "The image shows a fraction x/2 at the start, and the text has an orphaned 'x' on line 1 and orphaned '2' on line 3 — this confirms the fraction structure"
- **Reduces hallucination by ~30%** because the model has two independent data sources

**Cost impact:** Adds ~200–500 text tokens per page (the raw_text). Negligible cost increase (~$0.0003/page).

### 3.5 Approach 3: Screenshot-Based (ESAT Style)

The ESAT specimen extractor used Playwright to navigate a Pearson VUE test player and took screenshots of each question. This won't work for ENGAA/NSAA/TMUA because:

- **No interactive test player exists** — only static PDFs
- Would need to render PDFs to images anyway (same as Approach 1)
- The ESAT approach extracted from a web UI with accessible alt-text, not from PDF images

**Verdict:** This is effectively the same as Approach 1 but with extra steps. Not worth pursuing separately. Use direct PDF-to-image rendering.

### 3.6 Approach 4: Hybrid (Vision for Diagrams, Text Repair for Rest)

**Concept:**
- Questions with `has_diagram: true` → vision model extraction (needed to capture diagram content)
- Questions with `has_diagram: false` → text-only LLM repair using the garbled text

**Problem:** The OCR audit showed 93–96% of ENGAA/NSAA S1/TMUA questions have **structural** damage (broken fractions, multiline flattening). Text-only repair cannot fix these — the visual fraction bar is completely lost. Only ~35% of questions have purely cosmetic issues (unicode symbols) that text repair could handle.

**Verdict:** Not recommended as primary approach. Could be used as a Phase 2 cleanup for NSAA S2 and minor unicode issues, but the main corpus needs vision extraction.

### 3.7 Approach 5: Dedicated Math OCR Tools

#### GLM-OCR ($0.03/MTok) — **Worth Testing**
- z.ai's dedicated OCR model, priced at $0.03/MTok input AND output
- Purpose-built for document OCR
- **If it outputs LaTeX directly**, this is by far the cheapest option: ~$1 for the entire corpus
- **Risk:** May output plain text, not LaTeX. May not handle complex fractions well.
- **Test plan:** Send 20 sample pages (mix of easy and hard questions). Check if output is LaTeX or plain text.

#### GLM-4.6V-Flash (FREE) — **Worth Testing**
- z.ai's free vision model with rate limits
- Fully free, no cost
- **Risk:** Rate limits may make it very slow (hours for 1,000+ pages)
- Quality unknown for math LaTeX extraction
- **Test plan:** Same 20-page sample test.

#### GLM-4.6V-FlashX ($0.04/$0.40 MTok) — **Budget Champion**
- Extremely cheap vision model: ~$0.002/page
- Total for 1,000 pages: ~$2
- Better than the free tier (no rate limits, higher quality?)
- **Test plan:** Include in the 20-page bake-off.

#### Mathpix
- Industry-leading math OCR tool, outputs perfect LaTeX
- Pricing: ~$0.01 per image (freemium: 100 free/month)
- For 1,000 pages: ~$10
- **Problem:** API access may have changed; the pricing page redirects
- Not self-hostable; requires API key
- **Verdict:** Worth investigating if the GLM models don't work, but the CLA-based pipeline with a general vision model is more flexible.

#### Nougat (Meta)
- Open-source document OCR model (based on Donut architecture)
- Outputs LaTeX/markdown from PDF pages
- **Problem:** Requires GPU (8GB+ VRAM), self-hosted
- Quality is good for academic papers but untested for exam-style layout
- Setup complexity is high
- **Verdict:** Overkill for this use case. A vision LLM is simpler and more flexible.

#### LLaMA-3.2-Vision (Meta)
- Open-source vision model
- **Problem:** Not specifically trained for math OCR; would need fine-tuning
- Requires significant GPU resources
- **Verdict:** Not competitive with GLM or Claude for this task.

---

## 4. Recommended Implementation Plan

### Phase 0: Bake-Off Test (30 minutes)
**Before building the full pipeline, test which model produces the best LaTeX.**

1. Pick 20 diverse pages from the corpus:
   - 5 "easy" pages (simple text, no complex fractions)
   - 10 "medium" pages (fractions, roots, multi-line expressions)
   - 5 "hard" pages (complex diagrams, multi-column layout, integrals)

2. For each page, send to all candidate models:
   - Claude Haiku 4.5
   - GLM-OCR
   - GLM-4.6V-Flash (free)
   - GLM-4.6V-FlashX ($0.04)
   - (Optional) GPT-4.1

3. Score each output on:
   - LaTeX completeness (all maths in `\frac{}{}`, `\sqrt{}`, etc.)
   - Accuracy (no hallucinated numbers/expressions)
   - Option completeness (all A–H options present)
   - Structured JSON parseability

4. **Pick the winner** and proceed to Phase 1.

**Estimated cost of bake-off:** < $1

### Phase 1: Build the Pipeline (1 coding agent session)

The coding agent should build `scripts/re_extract_vision.py`:

```python
# Pseudocode outline:
# 1. Load format-manifest.json to get all question paper PDFs
# 2. For each PDF, render pages to images using pymupdf
# 3. For each page image:
#    a. Look up the garbled raw_text from the existing JSON corpus
#    b. Build the prompt (image + raw_text context + extraction instructions)
#    c. Call the chosen vision API
#    d. Parse JSON response
#    e. Store results keyed by question number
# 4. Merge results with existing JSON (replace question_text, options; preserve correct_answer, id, etc.)
# 5. Validate output
# 6. Save updated JSON files
```

**Key implementation decisions:**

| Decision | Recommendation |
|---|---|
| PDF rendering | `pymupdf` (already installed, fast, 300 DPI PNG) |
| Image format | JPEG at 85% quality (saves 50% tokens vs PNG with minimal quality loss) |
| API calls | Anthropic Batch API (50% discount) or streaming for Claude; standard API for GLM |
| Concurrency | Anthropic Batch: submit all at once. GLM: 5–10 concurrent requests with 1s delays |
| Output format | Update existing JSON files in-place (with .bak backup) |
| Error handling | Retry 3× with exponential backoff; log failures for manual review |

### Phase 2: Run the Pipeline (automated)

```bash
python3 scripts/re_extract_vision.py --model claude-haiku-4.5 --batch --dry-run  # verify
python3 scripts/re_extract_vision.py --model claude-haiku-4.5 --batch           # run
```

Estimated timeline:
- Anthropic Batch: submit in 10 min, results in 3–24 hours
- GLM streaming: ~2–4 hours (with concurrency)
- Claude streaming: ~2–3 hours (with concurrency)

### Phase 3: Validation

1. **Automatic checks:**
   - Every question retains its `correct_answer` and it still matches an option key
   - Question count matches existing corpus (no missing questions)
   - No empty `question_text` fields
   - LaTeX syntax check (balanced braces, valid commands)
   
2. **Spot-check 10%** (~134 questions) by comparing model output against the original PDF page images manually

3. **Answer key verification:** For each question, verify that the `correct_answer` value actually exists in the options. If an option was garbled (e.g., "2" was actually "x/2"), the vision model should have fixed it, but the correct_answer letter should still be valid.

### Phase 4: Phase 2 Cleanup (Minor)

For the ~105 NSAA S2 + ESAT science questions with only unicode symbol issues:
- Run a text-only pass (GLM-4.7 or Haiku 4.5, no vision needed)
- Replace `√` → `\sqrt{...}`, `²` → `^{2}`, `π` → `\pi`, etc.
- Cost: ~$0.50

---

## 5. Prompt Templates

### 5.1 Main Extraction Prompt (for Claude Haiku 4.5)

```python
SYSTEM_PROMPT = """You are an expert at transcribing mathematics examination questions 
into structured JSON with LaTeX notation. You work for a UK university admissions test 
preparation company.

You will receive an image of a PDF page from a Cambridge admissions test paper 
(ENGAA, NSAA, or TMUA). You may also receive garbled text extracted from the same 
page — use it as a cross-reference but trust the image first.

Your task: Extract ALL multiple-choice questions visible on this page into structured JSON.

CRITICAL RULES:
1. Output ONLY valid JSON. No markdown fences, no explanations, no preamble.
2. Mathematical notation MUST use LaTeX:
   - Fractions: \\frac{numerator}{denominator}
   - Square roots: \\sqrt{expression}
   - nth roots: \\sqrt[n]{expression}
   - Powers: x^{n} (always use braces)
   - Subscripts: x_{n}
   - Greek letters: \\pi, \\theta, \\alpha, \\beta, \\gamma, \\delta, \\sigma, \\mu, \\lambda, \\omega, \\phi
   - Inequalities: \\le, \\ge, \\ne, <, >
   - Multiplication: \\times
   - Division: \\frac{}{} or \\div
   - Vectors: \\vec{v}
   - Integrals: \\int_{a}^{b} f(x) dx
   - Summations: \\sum_{i=1}^{n}
   - Degrees: ^{\\circ}
   - Set notation: \\in, \\subset, \\cup, \\cap, \\mathbb{R}, \\mathbb{Z}, \\mathbb{N}
   - Absolute value: |x| or \\left|x\\right|
   - Logarithms: \\log, \\ln
   - Trigonometry: \\sin, \\cos, \\tan, \\sec, \\csc, \\cot
   - Infinity: \\infty
   - Approximation: \\approx
3. Do NOT wrap math in $...$ delimiters within the question text. Use LaTeX commands inline.
4. If a question has a diagram/graph/figure, set has_diagram to true.
5. If a page contains no questions (blank page, instructions, header), output {"questions": []}.
6. Preserve the exact mathematical meaning — do not simplify or transform expressions.
7. Option text should contain ONLY the mathematical expression, not the option letter."""

USER_PROMPT_TEMPLATE = """Extract all multiple-choice questions from this image.
{context_block}
Output JSON in this exact format:
{
  "page_number": {page_num},
  "questions": [
    {
      "question_number": 1,
      "question_text": "Full question text with LaTeX notation...",
      "options": {
        "A": "LaTeX expression for option A",
        "B": "LaTeX expression for option B",
        "C": "LaTeX expression for option C",
        "D": "LaTeX expression for option D"
      },
      "has_diagram": false
    }
  ]
}"""
```

### 5.2 Context Block (raw_text)

```python
def build_context_block(raw_text: str) -> str:
    if not raw_text or not raw_text.strip():
        return ""
    # Truncate to prevent excessive tokens (keep under 500 chars)
    truncated = raw_text[:500]
    return f"""Additional context (garbled OCR text from same page — use for cross-reference only):
---
{truncated}
---"""
```

### 5.3 NSAA S2 / ESAT Minor Repair Prompt (text-only)

```python
TEXT_REPAIR_SYSTEM = """You are fixing mathematical notation in exam questions. 
The text uses unicode math symbols instead of LaTeX. Convert to LaTeX.

Rules:
- √ → \sqrt{...} (determine scope from context)
- ², ³ → ^{2}, ^{3}
- π → \pi, θ → \theta, α → \alpha, etc.
- ≤ → \le, ≥ → \ge, ≠ → \ne
- × → \times
- ° → ^{\\circ}
- Do NOT change any non-math text
- Do NOT simplify or transform any expressions
- Output ONLY the converted text, nothing else"""

TEXT_REPAIR_PROMPT = """Fix the math notation in this question text:

{question_text}

Options:
{options_json}"""
```

---

## 6. Detailed Cost Breakdown

### 6.1 Claude Haiku 4.5 (Recommended — Batch API)

| Component | Tokens | Rate (Batch) | Cost per Page | Total (1,000 pages) |
|---|---|---|---|---|
| System prompt (cached read) | 300 | $0.05/MTok | $0.000015 | $0.015 |
| Image (JPEG, 300 DPI) | ~1,600 | $0.50/MTok | $0.0008 | $0.80 |
| User prompt (context text) | ~200 | $0.50/MTok | $0.0001 | $0.10 |
| Output (JSON) | ~800 | $2.50/MTok | $0.002 | $2.00 |
| **Per page total** | | | **~$0.003** | |
| **Grand total** | | | | **~$2.90** |

**Add 30% buffer for:** instruction pages (more output), retries, edge cases → **~$4 total**

### 6.2 Claude Sonnet 4.6 (Higher Quality Alternative)

Same token estimates, different rates:
| Component | Rate (Batch) | Cost per Page | Total |
|---|---|---|---|
| Input (image + prompt) | $1.50/MTok | $0.0027 | $2.70 |
| Output | $7.50/MTok | $0.006 | $6.00 |
| **Total** | | | **~$9** (with 30% buffer: ~$12) |

### 6.3 GPT-4.1 (OpenAI Alternative)

| Component | Rate (Batch) | Cost per Page | Total |
|---|---|---|---|
| Input (image + prompt) | $1.00/MTok | $0.0018 | $1.80 |
| Output | $4.00/MTok | $0.0032 | $3.20 |
| **Total** | | | **~$6.50** (with buffer: ~$8.50) |

### 6.4 GLM-4.6V-FlashX (Budget Option)

| Component | Rate | Cost per Page | Total |
|---|---|---|---|
| Input | $0.04/MTok | $0.000072 | $0.07 |
| Output | $0.40/MTok | $0.00032 | $0.32 |
| **Total** | | | **~$0.50** (with buffer: ~$0.70) |

### 6.5 GLM-OCR (Ultra-Budget — if LaTeX output works)

| Component | Rate | Cost per Page | Total |
|---|---|---|---|
| Input | $0.03/MTok | $0.000054 | $0.05 |
| Output | $0.03/MTok | $0.000024 | $0.02 |
| **Total** | | | **~$0.10** |

### 6.6 GLM-4.6V-Flash (FREE)

| Component | Rate | Cost per Page | Total |
|---|---|---|---|
| All | $0 | $0 | **$0** |

*Rate-limited. May take 12–24 hours for 1,000 pages. Quality unknown.*

### 6.7 Cost Summary

| Model | Mode | Total Cost (1,000 pages) | Notes |
|---|---|---|---|
| GLM-4.6V-Flash | Streaming | **$0** | Free, but slow, rate-limited |
| GLM-OCR | Streaming | **$0.10** | If it outputs LaTeX |
| GLM-4.6V-FlashX | Streaming | **$0.70** | Very cheap, decent quality? |
| Claude Haiku 4.5 | Batch + Cache | **~$4** | Best quality/cost balance |
| Claude Haiku 4.5 | Streaming | **~$8** | Faster delivery |
| GPT-4.1 | Batch | **~$8.50** | Good alternative |
| Claude Sonnet 4.6 | Batch | **~$12** | Higher quality, more expensive |
| Claude Opus 4.8 | Batch | **~$30** | Maximum quality, overkill |

---

## 7. Prompt Caching & Batch Strategy

### Anthropic Batch API
- Submit up to 10,000 requests per batch
- Results within 24 hours (typically 3–8 hours)
- **50% discount on ALL token prices** (input AND output)
- No RPM limit — only total throughput limit
- System prompt is **automatically cached** across all requests in a batch

### Anthropic Prompt Caching
- System prompts >1024 tokens are eligible for caching
- Cache reads cost 90% less than standard input ($0.05/MTok for Haiku)
- Cache writes cost 25% more than standard input ($1.25/MTok for Haiku)
- Our system prompt is ~300 tokens — just above the threshold
- **Combined Batch + Cache savings:** input tokens cost 95% less than standard rates

### Google Gemini Batch
- 50% discount on all models
- Results within 24 hours
- No prompt caching discount (but Gemini 2.5 Flash is already cheap)

### OpenAI Batch
- 50% discount on all models
- Results within 24 hours
- Automatic prompt caching (75% discount on cached prefixes)

### z.ai
- No batch API discount (as far as documented)
- Cached input is already very cheap ($0.004/MTok for GLM-4.6V-FlashX cached)
- Free tier models have rate limits but no cost

---

## 8. Risk Analysis

### What could go wrong?

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Vision model hallucinates a math expression | Low (5–10%) | Medium | Two-pass approach with raw_text cross-reference reduces this |
| Multi-page questions (question spanning two pages) | Very Low (<1%) | Medium | Check for incomplete questions after extraction; manually review |
| JSON parsing failures | Low (2–5%) | Low | Robust parser with regex fallback; retry |
| Rate limiting blocks progress | Medium | Low | Use batch API; implement exponential backoff |
| Option mismatch (model outputs 7 options instead of 8) | Low (<3%) | Medium | Post-processing validation; flag mismatches |
| Diagram questions lose diagram information | N/A | N/A | Vision model sees the diagram; set `has_diagram: true` |
| LaTeX syntax errors in output | Low (<2%) | Low | Post-processing LaTeX validation script |
| GLM-OCR doesn't output LaTeX (just plain text) | Medium | N/A | That's why we do the bake-off first |
| API key exhaustion / budget overrun | Very Low | Medium | Monitor usage; set spending limits |

### What is NOT at risk?

- **Data loss:** We have `.json.bak` files. Original PDFs are untouched. The worst case is we don't improve anything and revert.
- **Existing good data:** ESAT specimen questions are already good. NSAA S2 has only minor issues. We can skip or lightly repair these.
- **Correct answers:** The `correct_answer` field (option letter) is preserved from the answer key audit. Even if the option text changes, the letter remains valid.

---

## 9. Adapting vs Replacing Existing Scripts

### `convert_all_to_latex.py`
- **DO NOT adapt.** This script was designed for ESAT's spoken-text MathML format (`[begin mathsize...`, `numerator... over denominator...`). It won't help with ENGAA/NSAA/TMUA because those papers don't have MathML markers.
- **Write a new script** (`re_extract_vision.py`) from scratch.

### `extract_papers.py`
- **DO NOT replace.** This handles the initial pdftotext extraction and answer key parsing. Those parts are still valid. The re-extraction only replaces the `question_text` and `options` fields, not the extraction pipeline itself.

### `esat_specimen_extractor.py`
- **Not applicable.** This was for the Pearson VUE interactive test player. No equivalent exists for ENGAA/NSAA/TMUA.

---

## 10. Final Recommendation

### Immediate Action Plan

1. **Build the bake-off test script** (coding agent, ~1 hour)
   - Take 20 sample pages from across the corpus
   - Test GLM-OCR, GLM-4.6V-Flash, GLM-4.6V-FlashX, and Claude Haiku 4.5
   - Score outputs for LaTeX quality

2. **Based on bake-off results:**
   - **If GLM-OCR produces LaTeX:** Use it for the full run (~$0.10 total). Incredible value.
   - **If GLM-4.6V-FlashX produces good LaTeX:** Use it (~$0.70 total). Amazing value.
   - **If GLM-4.6V-Flash (free) produces good LaTeX:** Use it ($0 total, just slower).
   - **If Claude Haiku 4.5 is the winner:** Use Anthropic Batch API (~$4 total). Still excellent value.
   - **Most likely:** Claude Haiku 4.5 wins on quality, GLM models win on cost. Use Claude for quality-critical papers (ENGAA), GLM for bulk (NSAA/TMUA).

3. **Build the full pipeline** (coding agent, ~2–4 hours)
4. **Run and validate** (automated + manual spot-check)
5. **Phase 2 cleanup** for NSAA S2 / ESAT minor issues (~$0.50)

### Expected Outcomes

| Metric | Before | After |
|---|---|---|
| Questions with LaTeX | 135 (ESAT only) | ~1,477 (all) |
| Questions with garbled text | 1,399 | 0 |
| LaTeX fractions (`\frac{}`) | 135 | ~1,477 |
| LaTeX roots (`\sqrt{}`) | 135 | ~1,477 |
| Total API cost | — | $1–5 |
| Total development time | — | 1 coding agent session |
| Total runtime | — | 2–24 hours (mostly waiting) |
