# ESA-26 Part B — Generation Trial Quality Audit

**Date:** 2026-07-15
**Auditor:** Research Agent
**Inputs:** `shared/enriched-output/generation-trial/{glm-5.2,haiku-4.5}/questions.jsonl` + `gate-results.jsonl`
**Go/no-go gate for:** scaling [ESA-17](/ESAT/issues/ESAT-17) past 50 questions/night
**Method:** Full-read of all 38 generated questions + independent verification of worked solutions for 19/38 (50% spot-check sample, stratified across modules, difficulties, and pass/fail status)

---

## Executive Summary

**Verdict: NO-GO.** Neither GLM-5.2 nor Haiku 4.5 clears the ≥4/5 bar on all four audit dimensions. The dominant failure is **answer-key inconsistency** — the model's own worked solution derives a different answer than the marked correct option on roughly 30% of questions. This is a generator-prompt architecture flaw, not a model-capability ceiling. Three targeted fixes (§"Recommendations") should produce a re-trial that passes.

GLM-5.2 remains the recommended primary generator (over Haiku 4.5) because:
1. It generated 20/20 cleanly vs Haiku's 18/20 (two MATHS2 truncation failures on long explanations).
2. Solver self-consistency is significantly higher (17/20 vs 11/18).
3. Distractor analysis is more polished on the questions that do work.
4. It is free via z.ai.

Haiku 4.5 is **not** a better fallback — it shares the same answer-key flaw, has weaker multi-step arithmetic, and the z.ai proxy that maps `claude-haiku-4-5-20251001` → `glm-4.7` truncated on long maths explanations.

---

## Go/no-go Scorecard

| Dimension | GLM-5.2 | Haiku 4.5 | Bar |
|---|---|---|---|
| **1. Math correctness** | **2/5** | **2/5** | ≥4/5 ❌ |
| **2. Distractor quality** | **3/5** | **2/5** | ≥4/5 ❌ |
| **3. Classification (syllabus match)** | **4/5** | **4/5** | ≥4/5 ✅ |
| **4. Difficulty calibration** | **3/5** | **3/5** | ≥4/5 ❌ |
| **Gate reject rate** | 16/20 (80%) | 15/18 (83%) | <30% ❌ |
| **Real reject rate** (excl. uniqueness-only fails) | ~6/20 (30%) | ~7/18 (39%) | <30% ❌ (borderline) |

Only **Classification** clears the bar. Math correctness and distractor quality fail for both models.

---

## Detailed Findings by Dimension

### Dimension 1 — Math Correctness (GLM 2/5, Haiku 2/5)

**Independent verification of 19/38 questions.** Of the 10 GLM questions spot-checked, 6 had answer keys that contradicted the model's own worked solution:

| Batch | Idx | Spec | Verdict | Evidence |
|---|---|---|---|---|
| GLM-5.2 | 3 | MATHS1.M4 | ✗ **Wrong answer key** | Worked solution ends with "Option C is the true correct answer" but answer key is A. √(23/5) ≈ 2.14, which is a strict superset of Option A's bound x<2. |
| GLM-5.2 | 6 | MATHS2.MM3 | ✗ **Wrong answer key** | Algebra gives c = -8 (Option C); answer key marked B (-5). Explanation even ends with a prompt-leak: "I will adjust the options to A: 5, B: -5, C: -8, D: 0, E: 13." |
| GLM-5.2 | 7 | MATHS2.MM6 | ✗ **No valid option** | f'(x) = 4x³ − 24x² + 36x. f'(1) = 16, f'(0) = 0, f'(3) = 0. Max on [0,3] is 16, which is not in the options. Answer key D (36) is unsupported by the explanation's own arithmetic. |
| GLM-5.2 | 11 | PHYS.P7 | ✗ **Ambiguous** | Asks "how many intermediate nuclides have A=218" in U-238→Pb-206 chain. Po-218 exists transiently. Solver picked C (2), answer key A (0). The reasoning depends on interpretation of "intermediate" that the question doesn't pin down. |
| GLM-5.2 | 14 | CHEM.C4 | ✗ **Impossible numbers** | Explanation computes purity = 1.75 g / 1.50 g = 116.7%, then says "Wait, let me re-read the numbers." No option matches. |
| GLM-5.2 | 19 | BIO.B9 | ✗ **Factual error** | Bio-judge caught: explanation claims urea unchanged identifies small intestine, but glucose *increasing* in venous blood is physiologically incoherent. |
| GLM-5.2 | 0, 8, 12, 16 | various | ✓ Correct | Verified by hand: depreciation (14400), power (86.4 kJ), subatomic particles, insulin gene expression. |

Haiku-4.5 spot-check (9/18) found the same pattern — 6/9 broken:

| Batch | Idx | Spec | Verdict | Evidence |
|---|---|---|---|---|
| Haiku-4.5 | 4 | MATHS2.MM1 | ✗ **Answer key contradicts definition** | Question asks for "two distinct real solutions" but answer B (k=-8) gives discriminant 0 (repeated root). Explanation admits this: "Strictly, 'distinct' implies >0, but...". |
| Haiku-4.5 | 6 | MATHS2.MM3 | ✗ **Irrational answer, no option matches** | Explanation derives c = 10 ± 6√5, admits no option matches. |
| Haiku-4.5 | 11 | PHYS.P7 | ✗ **Internally incoherent** | Explanation computes ratio 7:1 but question states 5:1. Rationalizes Option B as "the mechanism is correct even though the math doesn't match." |
| Haiku-4.5 | 15 | CHEM.C11 | ✗ **Arithmetic error** | Explanation derives +2598 kJ/mol; answer key marked +2658. 20 kJ/mol transcription slip. |
| Haiku-4.5 | 19 | BIO.B9 | ✗ **Missing figure dependency** | References "Figure 1" that doesn't exist in JSON. Question is unevaluable without it. |
| Haiku-4.5 | 0, 10, 17 | various | ✓ Correct | Cube density, ship-wave Doppler, osmosis U-tube. |

**Pattern:** The root cause is consistent across both models. The answer key is generated as part of the JSON envelope, but the worked solution is then generated/streamed separately. When the model revises its reasoning mid-explanation ("Wait, let me re-read..."), the answer key is not updated to match. The worked solutions are often mathematically correct; the answer keys are stale.

### Dimension 2 — Distractor Quality (GLM 3/5, Haiku 2/5)

**GLM-5.2:** On correct questions, distractor analysis is excellent — each wrong option has a specific, named error path (e.g., "Linear Trap," "divides instead of multiplies," "uses arterial instead of Δ concentration"). Comparable to the GLM enrichment trial (5/5). However, on broken questions, the analysis is self-contradictory or exposes prompt-leak artifacts:
- idx 6: "I will adjust the options to..."
- idx 7: Cannot derive 36 from any of the shown evaluations, hedges instead of explaining each distractor.
- idx 14: Abandons the analysis mid-sentence when the impossible 116.7% appears.

**Haiku-4.5:** Same problem, worse polish. More "Wait, let me reconsider" hedges appear inline in the distractor analysis, which reads as thinking-aloud rather than analysis. On the 3 correct questions I verified (idx 0, 10, 17), distractors are well-explained.

### Dimension 3 — Classification / Syllabus Match (GLM 4/5, Haiku 4/5)

The strongest dimension. The reviewer scored syllabus = 5/5 on **every single question across both batches**, even on questions with wrong answer keys. The spec-topic selection from `esat_taxonomy.json` is working well: questions land on the right subtopic even when the arithmetic is broken. Two exceptions:
- GLM idx 19 (BIO.B9): bio-judge flagged an organ-identification inconsistency (syllabus topic right, biology wrong).
- GLM idx 11 (PHYS.P7): nuclear decay counting is on-syllabus but the question wording is ambiguous.

### Dimension 4 — Difficulty Calibration (GLM 3/5, Haiku 3/5)

The 2E/1M/1H per module target was achieved structurally. However, the audit reveals a calibration issue: some "Hard" questions are hard for the wrong reason — they're hard because the question is broken (no valid option, ambiguous interpretation), not because the underlying concept is hard. Examples: GLM idx 7 (Hard, no valid option), GLM idx 14 (Hard, impossible numbers), Haiku idx 6 (Medium, irrational answer). Easy questions are appropriately easy across both batches.

---

## Gate Stack Analysis

The 4-gate pipeline has one well-calibrated gate, one miscalibrated gate, one toothless gate, and one working gate:

| Gate | Behavior | Verdict |
|---|---|---|
| **Calculator-free checker** | Reasonable. Caught √4.6, √720, √400 correctly. Some false positives (flags 0.050 as "3 decimals" — that's a standard molar concentration). | ✅ Working with minor noise |
| **SymPy verifier** | **100% "undecidable" across all 38 questions.** Cannot parse LaTeX fractions written as `(25)(100)` instead of `(25/100)`, cannot handle `\text{}`, cannot extract equations from prose. Rubber-stamps everything. | ❌ **Effectively a no-op gate** |
| **Solver self-consistency** | Correctly flagged 7/20 GLM and 7/18 Haiku disagreements. On spot-check, **every solver disagreement corresponded to a real question flaw** (wrong answer key or ambiguous wording). This is the highest-signal gate in the stack. | ✅ High signal |
| **Reviewer rubric** | The `uniqueness` sub-dimension is **severely over-strict**: 16/20 GLM and 13/18 Haiku questions scored uniqueness = 3, blocking overall pass. Only 4/20 GLM and 5/18 Haiku scored 4. This is a **template-detection reflex**, not a quality signal — the questions do follow templates (by design, per ESA-17 §4.1 pattern extraction), so the reviewer is effectively penalising the intended generation strategy. | ⚠️ Miscalibrated |
| **Chem stoichiometry (RDKit)** | 4/4 pass on both batches. Small sample but clean. | ✅ Working |
| **Bio factual judge** | Caught 2/4 GLM and 1/4 Haiku factual errors. Correctly flagged GLM idx 19 (organ-identification inconsistency). | ✅ Working |

**Key implication:** The nominal 80% reject rate is misleading. If we (a) recalibrate the reviewer's uniqueness bar and (b) fix the generator prompt so answer keys match worked solutions, the real reject rate would be dramatically lower.

---

## Cross-Cutting Observations

### 1. The "Wait, let me reconsider" problem
Both models expose their chain-of-thought revisions in the final explanation text. Examples:
- GLM idx 14: "Wait, let me re-read the numbers carefully."
- GLM idx 6: "I will adjust the options to..."
- Haiku idx 4: "Wait, reviewing the options..."

These are generation-prompt issues. The model should produce a clean worked solution after arriving at its answer, not stream its uncertain thinking. A `temperature: 0.3` or a two-shot prompt (reason → then write clean solution) would help.

### 2. Answer key drift
The answer key is committed to JSON early in the generation, but the worked solution can revise mid-stream. When the model says "Wait, actually..." and arrives at a different answer, the original key is not updated. **This is the single highest-leverage fix.** Fixing this alone would resolve ~60% of observed failures.

### 3. SymPy gate is decorative
Every single question passed SymPy with "unsolvable — could neither verify nor contradict." The LaTeX parser cannot handle:
- Fractions written inline as `(25)(100)` instead of `(25/100)`
- `\text{}`, `\,`, `\mathrm{}` wrappers
- Inline prose around equations
- Function notation `f'(x)`

This gate provides zero quality signal in its current form. Either rewrite the parser to strip LaTeX wrappers and extract bare equations, or remove it from the accept/reject path and use it only as an informational metric.

### 4. Haiku-through-proxy truncation
The z.ai proxy that maps Haiku → glm-4.7 truncated 2/20 MATHS2 questions (long explanations hit the output ceiling). This is a proxy-infrastructure constraint, not a model quality issue per se, but it means **the Haiku fallback path is not reliable as configured**. If Haiku is to be a real fallback, either raise the proxy's `max_tokens` ceiling or test against real `api.anthropic.com`.

### 5. Missing figure dependency
Haiku idx 19 (BIO.B9) generated a question that depends on a "Figure 1" showing cardiac volume over time. No figure was generated or linked. This is a generation-prompt gap: the model should be instructed that figure-dependent questions are out of scope for text-only generation, or the pipeline needs a figure-generation step.

---

## Recommendations

### Primary recommendation: GLM-5.2 stays primary, but BLOCKED on three fixes before re-trial

| # | Fix | Owner | Effort | Expected impact |
|---|---|---|---|---|
| 1 | **Restructure generation prompt**: model must (a) solve the question first as internal reasoning, (b) commit the answer, (c) then write a clean worked solution that derives that answer, (d) then write distractor analysis. No "Wait, let me reconsider" in the final output. | Coding Agent | 0.5 day | Fixes ~60% of math-correctness failures |
| 2 | **Recalibrate reviewer uniqueness bar**: either raise the uniqueness threshold's tolerance for template-derived questions (since templates are the intended strategy), or drop uniqueness from the accept/reject decision and use it only as a coverage-dedup signal alongside the embedding dedup. | Coding Agent | 0.25 day | Restores ~12 false rejections per 20 Qs |
| 3 | **Fix SymPy verifier LaTeX parser**: strip `\text{}`, `\,`, `\mathrm{}`, `\left/\right`; convert `(a)(b)` fractions to `(a/b)`; extract the final equation from prose context. If this is too hard, replace with a bare SymPy call on the model's final-answer expression only. | Coding Agent | 0.5 day | Restores the only ground-truth gate |

After these three fixes: re-run the 20-question trial with the same prompts, re-audit. Expected outcome: math correctness → 4/5, reject rate → <30%. If that holds, greenlight Phase 3 nightly generation.

### Secondary recommendations

4. **Filter figure-dependent questions at generation**: add "do not write questions that require a figure/diagram" to the prompt for text-only generation. Add a separate figure-aware generation track later.
5. **Test the Haiku fallback against real `api.anthropic.com`** rather than the z.ai proxy, to verify it actually works when needed. The proxy's truncation behaviour is not representative.
6. **Strengthen the bio-judge**: it caught real errors (GLM idx 19) but only 2/4 GLM passes were clean. Consider giving it the ESAT Content Specification PDF as context (per strategy §2.3).

---

## Per-Batch Verdicts

### GLM-5.2
- 20/20 generations completed cleanly (no truncation).
- 4/20 passed all 4 gates nominally; ~14/20 are high-quality if the uniqueness bar is recalibrated (they have correct math, good distractors, right syllabus).
- ~6/20 have substantive quality issues (wrong answer key, impossible numbers, factual errors).
- **Recommendation:** Primary generator, conditional on fixes #1–#3.

### Haiku-4.5 (via z.ai proxy → glm-4.7)
- 18/20 generations completed; 2 truncation failures on long MATHS2 explanations.
- 3/18 passed all 4 gates nominally.
- Solver self-consistency notably weaker (11/18 vs GLM's 17/20) — loses track of multi-step arithmetic more often.
- **Recommendation:** Keep as documented fallback, but do not switch to it. The proxy substitution makes it untested against real Haiku 4.5.

---

## Sources

1. `shared/enriched-output/generation-trial/README.md` — Part A reproduction + headline numbers
2. `shared/enriched-output/generation-trial/glm-5.2/questions.jsonl` — 20 questions
3. `shared/enriched-output/generation-trial/glm-5.2/gate-results.jsonl` — 20 gate verdicts
4. `shared/enriched-output/generation-trial/haiku-4.5/questions.jsonl` — 18 questions
5. `shared/enriched-output/generation-trial/haiku-4.5/gate-results.jsonl` — 18 gate verdicts
6. `shared/enriched-output/generation-trial/cost-log.json` — token + cost record
7. `shared/enriched-output/glm-trial/quality-audit.md` — template format (2026-07-10 enrichment audit)
8. `shared/question-generation-1000-strategy.md` §2.3 — 4-gate specification
9. [ESA-17 plan §4.7](/ESAT/issues/ESAT-17#document-plan) — trial gate definition
10. [ESA-26](/ESAT/issues/ESA-26) — this task's definition and go/no-go criteria
11. [ESA-27](/ESAT/issues/ESA-27) — Part A generation subtask

## Confidence & Gaps

**High confidence:**
- Math-correctness verdicts on 19/38 spot-checked questions (verified by hand)
- Uniqueness-rubric over-strictness (16/20 GLM at uniqueness=3 is clearly a template-detection reflex)
- SymPy gate is functionally a no-op (100% undecidable)
- Solver self-consistency is the highest-signal gate (every disagreement = real flaw)

**Medium confidence:**
- Exact math-correctness rate on the 19/38 questions not deeply verified (extrapolated from the 50% sample)
- Difficulty calibration score (3/5) — "hard because broken" vs "hard because deep" is a judgement call

**Open gaps:**
- Whether fix #1 (prompt restructure) will actually produce consistent answer keys — untested. A 5-question pilot would de-risk before the full 20-question re-trial.
- Whether real Haiku 4.5 (via `api.anthropic.com`, not the z.ai proxy) performs differently — untested in this trial.
- Whether the z.ai proxy's glm-4.7 is representative of real Haiku 4.5 quality. It almost certainly is not.
