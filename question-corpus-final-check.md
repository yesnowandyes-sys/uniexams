# Question Corpus Final Check Report

**Date:** 2026-07-08  
**Auditor:** Subagent (automated scan)  
**Scope:** All JSON question files across 5 exam types

---

## Summary: ✅ READY FOR OPUS ENRICHMENT

The corpus contains **1,687 questions across 48 JSON files** spanning 5 exam types. All critical fields (question text, options, correct answer) are present at 100% coverage. No within-file duplicates exist. Cross-paper duplicates are exclusively ENGAA↔NSAA shared Section 1 questions (expected overlap). No blockers found.

---

## 1. Question Counts by Exam Type

| Exam Type | Files | Questions | Year Range |
|-----------|-------|-----------|------------|
| **ESAT** (specimen) | 5 | 135 | specimen |
| **ENGAA** | 8 | 362 | 2016–2023 |
| **NSAA** (S1) | 8 | 680 | 2016–2023 |
| **NSAA S2** | 12 | 210 | 2020–2022 + specimen |
| **TMUA** | 15 | 300 | specimen + 2017–2023 |
| **TOTAL** | **48** | **1,687** | |

### Per-File Breakdown

#### ESAT Specimen Papers (5 files, 135 questions)
- `esat_specimen_maths1.json`: 27
- `esat_specimen_maths2.json`: 27
- `esat_specimen_physics.json`: 27
- `esat_specimen_chemistry.json`: 27
- `esat_specimen_biology.json`: 27

#### ENGAA Section 1 (8 files, 362 questions)
- `2016_s1.json`: 54
- `2017_s1.json`: 54
- `2018_s1.json`: 54
- `2019_s1.json`–`2023_s1.json`: 40 each (×5 = 200)

#### NSAA Section 1 (8 files, 680 questions)
- `2016_s1.json`–`2019_s1.json`: 90 each (×4 = 360)
- `2020_s1.json`–`2023_s1.json`: 80 each (×4 = 320)

#### NSAA Section 2 (12 files, 210 questions)
- Biology/Chemistry/Physics × 3 year sets (2020, 2021, 2022) = 9 files × 20 = 180
- Specimen Biology/Chemistry/Physics = 3 files × 10 = 30

#### TMUA (15 files, 300 questions)
- `specimen_p1.json` + `specimen_p2.json`: 20 each
- `2017_p2.json`: 20 (no 2017 P1 in corpus)
- `2018_p1.json`–`2023_p2.json`: 20 each ×12 files = 240

---

## 2. Field Completeness

| Field | Present | % | Status |
|-------|---------|---|--------|
| `id` | 1,687 | 100% | ✅ Complete |
| `year` | 1,687 | 100% | ✅ Complete |
| `paper` | 1,687 | 100% | ✅ Complete |
| `question_number` | 1,687 | 100% | ✅ Complete |
| `question_text` | 1,687 | 100% | ✅ Complete |
| `options` | 1,687 | 100% | ✅ Complete |
| `correct_answer` | 1,687 | 100% | ✅ Complete |
| `section` | 1,552 | 92% | ⚠️ ESAT specimen papers lack this (expected — single-section papers) |
| `has_diagram` | 1,552 | 92% | ⚠️ ESAT specimen papers lack this |
| `raw_text` | 1,342 | 80% | ⚠️ ESAT specimen papers lack this |
| `subject` | 210 | 12% | ⚠️ Only NSAA S2 has subject field |
| `module` | 135 | 8% | ⚠️ Only ESAT specimen has module field |
| `explanation` | 135 | 8% | ℹ️ Only ESAT specimen has explanations |

**Critical fields (question_text, options, correct_answer): 100% coverage — zero missing values.**

### Data Schema Variations

Three distinct schemas exist across the corpus:

**Schema A — ENGAA/NSAA S1/TMUA** (1,342 questions):
```json
{id, year, paper, section, question_number, question_text, has_diagram, options, correct_answer, raw_text, diagram_images}
```

**Schema B — NSAA S2** (210 questions):
```json
{id, year, paper, section, subject, part, question_number, question_text, has_diagram, diagram_images, options, correct_answer}
```

**Schema C — ESAT Specimen** (135 questions):
```json
{id, year, paper, module, question_number, question_text, question_images, screenshot, explanation_screenshot, options, options_detailed, correct_answer, correct_answer_raw, correct_answer_plain, correct_answer_images, explanation, explanation_images, extracted_at}
```

These schema differences are expected given different extraction workflows. No conflicts.

---

## 3. Duplicates

### Within-File Duplicates: ✅ NONE

Zero within-file duplicate questions detected across all 48 files.

### Cross-Paper Duplicates: 38 Groups (ENGAA↔NSAA)

All 38 cross-paper duplicate groups are **ENGAA-NSAA shared Section 1 questions**. This is expected and correct — ENGAA and NSAA shared a common Section 1 from 2016–2023, with questions appearing in both exams (sometimes at different question numbers).

| Year | Shared Questions |
|------|-----------------|
| 2017 | 2 (Q1, Q25↔Q16) |
| 2018 | 3 (Q1, Q9↔Q6, Q23↔Q16) |
| 2019 | 2 (Q1, Q3) |
| 2020 | 3 (Q5, Q11, Q17) |
| 2021 | 10 (every odd Q1-Q19) |
| 2022 | 8 (every other from Q3-Q17) |
| 2023 | 10 (every other from Q1-Q19) |

**Verdict:** These are genuine shared questions, not extraction errors. Opus enrichment should deduplicate or tag them as shared. This is NOT a blocker but should be handled during enrichment.

---

## 4. Topic/Subject Classification

### Current State
- **NSAA S2** (210 questions): Has `subject` field (biology/chemistry/physics) — ✅ correct
- **ESAT Specimen** (135 questions): Has `module` field (maths1/maths2/physics/chemistry/biology) — ✅ correct
- **ENGAA, NSAA S1, TMUA** (1,342 questions): No per-question subject/topic field — ⚠️ **this is expected**

ENGAA and NSAA S1 papers are multi-subject (maths + physics + chemistry + biology mixed). Individual questions aren't tagged with their subject. TMUA is pure maths so no subject tagging is needed.

### This is an Enrichment Target, Not a Bug
The whole point of Opus enrichment is to classify these 1,342 untagged questions into the taxonomy. The corpus is structurally ready for this.

---

## 5. Taxonomy Coverage

`esat_taxonomy.json` (version 2026-07-07) covers all 5 ESAT modules:
- **M1** Mathematics 1 (Units, Number, Ratio, Algebra, Geometry, Statistics, Probability)
- **M2** Mathematics 2 (further maths topics)
- **P** Physics
- **C** Chemistry  
- **B** Biology

The taxonomy is comprehensive and well-structured with spec codes, topic names, subtopics, and skill descriptions. It provides a solid classification framework for Opus enrichment.

---

## 6. Format Manifest Review

All 52 source PDFs in `format-manifest.json` show:
- **Extraction tool:** both (pdftotext + pymupdf)
- **Text quality:** clean
- **Status:** clean (no OCR issues, no garbled text)

No extraction problems noted. The manifest includes ENGAA (2016–2023), NSAA (2016–2023), and TMUA (2016–2023 + specimen). ESAT specimen papers were extracted separately and aren't in the manifest (they came from a different source).

---

## 7. Issues & Blockers

### 🟢 No Blockers
- All 1,687 questions have question text, options, and correct answers
- No malformed JSON files
- No within-file duplicates
- Cross-paper duplicates are expected ENGAA-NSAA overlap
- All source PDFs extracted cleanly

### 🟡 Things to Address During/Before Enrichment

1. **ENGAA-NSAA deduplication** — 38 shared questions. Decide strategy: keep both with `shared_with` tag, or deduplicate to single entries with dual exam IDs.

2. **Schema harmonisation** — Three different field schemas. Opus enrichment prompt should output a single unified schema. Consider adding `exam_type`, `subject`, and `topic_code` to all questions.

3. **TMUA 2016 gap** — Format manifest has TMUA-2016-paper-1.pdf and TMUA-2016-paper-2.pdf listed, but no JSON files exist for 2016. Also no 2017_p1.json. This isn't a blocker for the trial but is a coverage gap.

4. **ENGAA 2016 answer key** — Format manifest notes "Very small file" (6,598 bytes). All ENGAA questions appear to have correct answers populated, so this likely didn't cause issues.

---

## 8. Overall Assessment

### Data Quality: ⭐⭐⭐⭐⭐ Excellent

The corpus is well-structured, complete, and ready for Opus enrichment. The core data (question text, options, correct answers) has 100% coverage with no missing or malformed entries. The lack of topic classification on 1,342 questions is exactly the gap Opus enrichment is designed to fill.

### Recommended Next Steps
1. Define the output schema for enriched questions
2. Decide deduplication strategy for ENGAA-NSAA shared questions
3. Prepare Opus prompt with taxonomy + classification instructions
4. Run trial enrichment on a small batch (e.g., one ENGAA paper = 40 questions)
5. Validate outputs, then scale to full corpus

**Verdict: PROCEED with trial run.** 🚀
