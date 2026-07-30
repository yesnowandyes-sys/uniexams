# LaTeX Quality Audit Report

**Date:** 2026-07-10  
**Scope:** All 1,342 questions across ENGAA, NSAA, TMUA corpora  
**Method:** Automated structural checks on every question + manual math verification on 20 questions

---

## 1. Pass/Fail Summary

| Metric | Count | Percentage |
|--------|-------|-----------|
| **Total questions** | 1,342 | 100% |
| **Questions passing all checks** | 1,260 | 93.9% |
| **Questions with at least one issue** | 82 | 6.1% |
| **Questions with critical issues** | 25 | 1.9% |

> **Critical issues** = unmatched braces, invalid correct_answer, or empty options. These will cause rendering failures or incorrect answers in the enrichment pipeline.

---

## 2. Issue Breakdown by Category

| Issue Category | Unique Questions | Severity | Description |
|---------------|-----------------|----------|-------------|
| **options_latex key mismatch** | 36 | Low | `options_latex` has fewer keys than `options` — some options lack LaTeX formatting |
| **Unmatched braces** | 20 | **High** | Systematic `{-^{` pattern causes broken LaTeX rendering |
| **Unicode math mixed with LaTeX** | 14 | Low | Unicode symbols (θ, ², ≥, →) used alongside LaTeX commands |
| **Non-printable bytes in question_text** | 10 | Medium | `\r` (carriage return), `\x08` (backspace), `\x0c` (form feed) in text |
| **correct_answer not in options** | 5 | **High** | Answer letter references an option that doesn't exist in the `options` dict |
| **Empty options (non-diagram)** | 1 | **High** | TMUA-2020-P2-Q5 has all empty options but `has_diagram=False` |

### Note on `raw_text` non-printable bytes
722 questions (53.8%) have `\x0c` (form feed) bytes in their `raw_text` field. This is an OCR artifact and **does not affect rendering** since `raw_text` is not used for display. These are excluded from the issue count above.

---

## 3. Detailed Issue List

### 3.1 Unmatched Braces (20 questions) — CRITICAL

All 20 are caused by two systematic OCR/transcription patterns:

**Pattern A: `{-^{1}` (should be `^{-1}`)** — 17 questions
This pattern appears in physics units like `kg^{-^{1}` (should be `kg^{-1}`) and velocity units `m s^{-^{1}`. The extra `-{` opens a brace that never closes, causing LaTeX compilation errors.

| Paper | Questions |
|-------|-----------|
| ENGAA-2016-S1 | Q18 |
| ENGAA-2018-S1 | Q18, Q36, Q54 |
| ENGAA-2019-S1 | Q24 |
| ENGAA-2020-S1 | Q18 |
| NSAA-2016-S1 | Q54, Q80 |
| NSAA-2017-S1 | Q82 |
| NSAA-2018-S1 | Q32, Q90 |
| NSAA-2019-S1 | Q51, Q52, Q76 |
| NSAA-2020-S1 | Q54 |
| NSAA-2021-S1 | Q55 |
| NSAA-2023-S1 | Q28 |

**Pattern B: `β^{-` (should be `β^-`)** — 3 questions
The `{` after `β^-` is unclosed in particle physics notation.

| Paper | Questions |
|-------|-----------|
| NSAA-2017-S1 | Q27 |
| NSAA-2018-S1 | Q33, Q88 |

**Fix:** Search-and-replace `{-^{` → `^{-` and `\beta^{-` → `\beta^-` (or `\beta^{-}`).

### 3.2 correct_answer Not in Options (5 questions) — CRITICAL

These questions have option letters in `correct_answer` that don't exist in the `options` dictionary. The options are likely truncated during OCR (original papers may have had more options).

| Question | correct_answer | Available Options | has_diagram |
|----------|---------------|-------------------|-------------|
| ENGAA-2016-S1-Q36 | H | A–E | True |
| ENGAA-2017-S1-Q40 | F | A–E | True |
| ENGAA-2020-S1-Q26 | H | A–G | False |
| ENGAA-2022-S1-Q28 | F | A–D | False |
| NSAA-2018-S1-Q84 | F | A–D | True |

**Note:** 3 of these have `has_diagram=True`, suggesting some options may have been image-based and lost during transcription. Even for diagram questions, the `correct_answer` letter should reference an existing option.

### 3.3 options_latex Key Mismatch (36 questions) — LOW

The `options_latex` dictionary has fewer keys than `options`, meaning some options don't have LaTeX-formatted versions. This affects rendering quality but doesn't break functionality (the plain `options` text serves as fallback).

Most affected papers: ENGAA-2016-S1 (6), TMUA-2017-P2 (4), TMUA-2019-P1 (3).

### 3.4 Non-printable Bytes in question_text (10 questions) — MEDIUM

| Question | Bytes | Papers Affected |
|----------|-------|----------------|
| ENGAA-2022-S1-Q1 | `\x0c` (form feed) | 1 |
| NSAA-2017-S1 (Q47, Q49, Q53) | `\r` (carriage return) | 3 |
| NSAA-2018-S1-Q38 | `\r` | 1 |
| NSAA-2019-S1 (Q44, Q48) | `\r` | 2 |
| NSAA-2022-S1-Q1 | `\r` | 1 |
| TMUA-2021-P1-Q2 | `\x08` (backspace) | 1 |
| TMUA-2022-P1-Q3 | `\x08` (backspace) | 1 |

**Fix:** Strip `\r`, `\x08`, `\x0c` from `question_text` fields.

### 3.5 Unicode Math Mixed with LaTeX (14 questions) — LOW

Unicode mathematical symbols appear in the same field as LaTeX commands. Most renderers handle this fine, but for consistency, all math should use LaTeX notation.

| Symbol | Count | Example Questions |
|--------|-------|-------------------|
| θ (theta) | 5 | ENGAA-2018-S1-Q38, ENGAA-2019-S1-Q37, NSAA-2019-S1-Q87, NSAA-2023-S1-Q10 |
| ² (superscript 2) | 2 | ENGAA-2017-S1-Q35, ENGAA-2022-S1-Q40 |
| ≥ (≥) | 3 | NSAA-2017-S1-Q8, TMUA-2021-P2-Q20, TMUA-2022-P1-Q14 |
| → (arrow) | 2 | NSAA-2017-S1-Q74, NSAA-2021-S1-Q55 |
| ≤ (≤) | 1 | TMUA-2019-P1-Q8 |
| × (×) | 1 | NSAA-2017-S1-Q28 |
| • (bullet) | 1 | NSAA-2023-S1-Q54 |
| α, β (mixed with θ) | 1 | ENGAA-2019-S1-Q37 |

### 3.6 Empty Options — Non-Diagram Question (1 question) — CRITICAL

**TMUA-2020-P2-Q5**: `has_diagram=False` but all 6 options (A–F) are empty strings. This is a graph-sketch question ("Which one of the following shows the graph of...") where the options should reference images. The `correct_answer=A` is preserved but meaningless without option content.

---

## 4. Per-Paper Breakdown

| Paper | Type | Questions | Issues | Issue Rate |
|-------|------|-----------|--------|-----------|
| ENGAA-2016_s1 | ENGAA | 54 | 7 | 13.0% |
| ENGAA-2017_s1 | ENGAA | 54 | 2 | 3.7% |
| ENGAA-2018_s1 | ENGAA | 54 | 4 | 7.4% |
| ENGAA-2019_s1 | ENGAA | 40 | 4 | 10.0% |
| ENGAA-2020_s1 | ENGAA | 40 | 4 | 10.0% |
| ENGAA-2021_s1 | ENGAA | 40 | 3 | 7.5% |
| ENGAA-2022_s1 | ENGAA | 40 | 4 | 10.0% |
| ENGAA-2023_s1 | ENGAA | 40 | 0 | 0.0% |
| NSAA-2016_s1 | NSAA | 90 | 2 | 2.2% |
| NSAA-2017_s1 | NSAA | 90 | 8 | 8.9% |
| NSAA-2018_s1 | NSAA | 90 | 5 | 5.6% |
| NSAA-2019_s1 | NSAA | 90 | 6 | 6.7% |
| NSAA-2020_s1 | NSAA | 80 | 1 | 1.2% |
| NSAA-2021_s1 | NSAA | 80 | 1 | 1.2% |
| NSAA-2022_s1 | NSAA | 80 | 1 | 1.2% |
| NSAA-2023_s1 | NSAA | 80 | 3 | 3.8% |
| TMUA-2017_p2 | TMUA | 20 | 4 | 20.0% |
| TMUA-2018_p1 | TMUA | 20 | 3 | 15.0% |
| TMUA-2018_p2 | TMUA | 20 | 1 | 5.0% |
| TMUA-2019_p1 | TMUA | 20 | 4 | 20.0% |
| TMUA-2019_p2 | TMUA | 20 | 0 | 0.0% |
| TMUA-2020_p1 | TMUA | 20 | 3 | 15.0% |
| TMUA-2020_p2 | TMUA | 20 | 3 | 15.0% |
| TMUA-2021_p1 | TMUA | 20 | 2 | 10.0% |
| TMUA-2021_p2 | TMUA | 20 | 4 | 20.0% |
| TMUA-2022_p1 | TMUA | 20 | 3 | 15.0% |
| TMUA-2022_p2 | TMUA | 20 | 0 | 0.0% |
| TMUA-2023_p1 | TMUA | 20 | 0 | 0.0% |
| TMUA-2023_p2 | TMUA | 20 | 0 | 0.0% |
| TMUA-specimen_p1 | TMUA | 20 | 0 | 0.0% |
| TMUA-specimen_p2 | TMUA | 20 | 0 | 0.0% |
| **TOTAL** | | **1,342** | **82** | **6.1%** |

### By Paper Type

| Type | Papers | Questions | Issues | Rate |
|------|--------|-----------|--------|------|
| ENGAA | 8 | 362 | 28 | 7.7% |
| NSAA | 8 | 680 | 27 | 4.0% |
| TMUA | 15 | 300 | 27 | 9.0% |

**Note:** TMUA's higher rate is driven by the `options_latex` key mismatch issue. Early TMUA papers (2017-2022) have many questions where `options_latex` only covers a subset of options.

---

## 5. Math Verification Results

20 questions were verified by actually solving the math from the LaTeX question text and comparing against the stated `correct_answer`.

### ENGAA (7 verified)

| Question | Problem | Expected | Verified |
|----------|---------|----------|----------|
| ENGAA-2016-S1-Q1 | Solve -8 < 6 - x/2 | G (x < 28) | ✅ |
| ENGAA-2017-S1-Q3 | 2x² ≥ 15 - x | E (x ≤ -3, x ≥ 2.5) | ✅ |
| ENGAA-2018-S1-Q47 | Coeff of x³ in (1-2x)⁵(1+2x)⁵ | D (0) | ✅ |
| ENGAA-2019-S1-Q35 | Coeff of x⁴ in ∫₀ˣ(3+2t)⁷ dt | E (5670) | ✅ |
| ENGAA-2020-S1-Q37 | Product of roots of (log₁₀x²)² + log₁₀x = 3 | D (10^(-1/4)) | ✅ |
| ENGAA-2021-S1-Q1 | Simplify 5xy²(5x²y)^(-3)(5x²y) | E (1/(5x³)) | ✅ |
| ENGAA-2020-S1-Q26 | ⚠️ correct_answer=H but options only A–G | — | ❌ |

### NSAA (7 verified)

| Question | Problem | Expected | Verified |
|----------|---------|----------|----------|
| NSAA-2016-S1-Q5 | Depreciation £15000 at 20%/yr × 2yr | C (£5400) | ✅ |
| NSAA-2016-S1-Q48 | Reverse activation energy | F (+250 kJ/mol) | ✅ |
| NSAA-2016-S1-Q81 | 7cosθ - 3tanθ sinθ = 1 | D (cosθ = 3/5 or -1/2) | ✅ |
| NSAA-2018-S1-Q8 | Right triangle area | F (54) | ✅ |
| NSAA-2018-S1-Q17 | (p-q)/(p+q) for sequence pn²+q | G (4) | ✅ |
| NSAA-2018-S1-Q23 | Energy wasted at 5% efficiency | E (57000 J) | ✅ |
| NSAA-2019-S1-Q85 | Coeff of x⁴ in ∫₀ˣ(3+2t)⁷ dt | E (5670) | ✅ |

### TMUA (6 verified)

| Question | Problem | Expected | Verified |
|----------|---------|----------|----------|
| TMUA-2018-P1-Q1 | ∫₁⁴(3-2x)/(x√x)dx | D (-1) | ✅ |
| TMUA-2019-P1-Q1 | Quadratic through (1,-1), vertex (-1,3) | A (-x²-2x+2) | ✅ |
| TMUA-2020-P1-Q1 | d/dx[(x³-5x²)/(2x√x)] | C ((3x-5)/(4√x)) | ✅ |
| TMUA-2021-P1-Q1 | Line through circle intersection points | F (5x-3y=4) | ✅ |
| TMUA-2022-P1-Q1 | Solutions of 2cos⁴θ-5cos²θ+3=0 | C (3) | ✅ |
| TMUA-2023-P1-Q1 | Simultaneous integrals, find a+b | F (4) | ✅ |

### Verification Summary

- **19 of 20 verified correct** ✅
- **1 flagged** ❌ (ENGAA-2020-S1-Q26 — has invalid correct_answer, likely truncated options)
- **0 wrong answers found** — where options are complete, the correct_answer always matches the math

---

## 6. Additional Notes

### Diagram Questions with Empty Options (Expected)
13 questions have all-empty `options` dictionaries but `has_diagram=True` and image files in `diagram_images`. These are image-based questions (pie charts, graph sketches, geometry) where options are visual. This is expected behavior — the `correct_answer` letter is preserved for reference.

### NSAA Format Questions
Several NSAA questions use "1, 2, 3" as statement labels and A–H as combination options. These are correctly structured and not an issue.

### NSAA "Option Z"
NSAA-2016-S1-Q44 uses option Z as the "odd one out" choice. This is an NSAA-specific format and not a sequencing error.

### `\x0c` in raw_text
722 questions have form feed characters (`\x0c`) in `raw_text`. This is an OCR artifact from page breaks. Since `raw_text` is not used for rendering, this is cosmetic only.

---

## 7. Overall Verdict

### 🟡 CONDITIONALLY READY — minor fixes recommended before enrichment pipeline

**The corpus is in good shape overall:**
- 93.9% of questions pass all automated checks
- Math is correct in all verified questions (19/20 with complete options)
- No broken LaTeX commands, no JSON parse errors
- No empty question_text fields
- All questions have at least 2 options

**Fixes needed before enrichment pipeline (26 critical issues):**

1. **Unmatched braces (20 questions)** — Systematic `{-^{` → `^{-` fix will resolve 17; `\beta^{-` → `\beta^-` fixes 3. **Automatable one-liner.**

2. **Invalid correct_answer (5 questions)** — Options were truncated during OCR. These questions should either be fixed (restore missing options from source) or excluded from the pipeline.

3. **Empty non-diagram question (1 question)** — TMUA-2020-P2-Q5 needs options restored or should be excluded.

**Recommended but not blocking:**
- Strip non-printable bytes from 10 `question_text` fields
- Complete `options_latex` for 36 questions (nice-to-have for consistent rendering)
- Normalize Unicode math to LaTeX in 14 questions

**Estimated fix time:** ~15 minutes of scripted cleanup for the brace issues + ~30 minutes of manual review for the 6 questions with missing/invalid options.
