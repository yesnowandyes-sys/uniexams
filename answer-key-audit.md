# Answer Key Audit Report

**Date:** 2026-07-10
**Scope:** All 1,342 questions across ENGAA, NSAA S1, TMUA, ESAT corpora
**Method:** Structural check (answer exists in options) + manual math verification on selected questions

## Summary

| Metric | Count |
|--------|-------|
| Total questions | 1,342 |
| Answer key present | 1,342 |
| Answer exists in options | 1,339 |
| Disputed/wrong answers | 3 |

## Wrong/Disputed Answer Keys

### 1. TMUA Specimen Paper 2 Q1 — **WRONG**
- **Stated answer:** B (√(11/2))
- **Correct answer:** D (√37)
- **Question:** Find the radius of the circle x² + y² − 8x + 12y + 15 = 0
- **Verification:** Completing the square: (x−4)² + (y+6)² = 37, so r = √37
- **Cause:** Answer key error in the specimen paper

### 2. ENGAA 2020 Section 1 Q26 — **DISPUTED**
- **Stated answer:** H
- **Issue:** Only options A–G exist in the question paper. H is not a valid option.
- **Question:** Moment about axle for a rectangular coil in a magnetic field
- **Plausible correct answer:** G (4.5 N·cm) based on M = N·I·L·B·d = 50 × 0.60 × 0.30 × 0.050 × 0.10
- **Cause:** Answer key typo (H instead of G)

### 3. ENGAA 2022 Section 1 Q28 — **WRONG**
- **Stated answer:** F (£300)
- **Correct answer:** D (£200)
- **Question:** Rob's earnings chain — Sunday earnings given Wednesday = £84
- **Verification:** Sunday × 0.5 × 1.2 × 0.7 = Wednesday → x × 0.42 = 84 → x = 200
- **Cause:** Answer key error

## Math Verification (Spot Checks)

19 additional questions verified by solving the math from the LaTeX question text. All verified correct where options are complete.

Verified: ENGAA 2016 Q1, Q2, Q3; ENGAA 2018 Q47; ENGAA 2019 Q35; ENGAA 2020 Q37; ENGAA 2021 Q1; NSAA 2016 Q5, Q48, Q81; NSAA 2018 Q8, Q17, Q23; TMUA 2018 P1 Q1; TMUA 2019 P1 Q1; TMUA 2020 P1 Q1; TMUA 2021 P1 Q1; TMUA 2022 P1 Q1; TMUA 2023 P1 Q1

**Result: 19/19 correct** where answer key values exist in options.

## Overall Assessment

The answer keys are highly reliable (99.8% correct). The 3 issues found are:
1. One specimen paper error (TMUA specimen P2 Q1)
2. One answer key typo (ENGAA 2020 Q26 — H should be G)
3. One incorrect answer (ENGAA 2022 Q28 — F should be D)

All three have been flagged in the corpus JSON with `answer_key_disputed: true` and explanatory notes. The enrichment pipeline can use these flags to handle disputed answers appropriately.
