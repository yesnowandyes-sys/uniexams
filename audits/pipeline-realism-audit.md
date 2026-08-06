# ESAT Question Generation Pipeline — Realism Audit

**Date:** 2026-08-05
**Scope:** Every mechanism used to make generated questions realistic to the real ESAT exam.
**Files audited:** 14 scripts, 7 quality gate modules, pattern files, research docs, taxonomy, weightings.

---

## 1. Topic Spread / Distribution

### How it works (three-tier priority system)

The coverage tracker (`scripts/coverage_tracker.py`, lines 113–170) resolves targets from **three sources** in priority order:

1. **`data/weightings.json`** (ESA-47) — corpus-weighted proportions derived from the actual enriched past-paper corpus by `scripts/compute_weightings.py`. Each question in the corpus contributes a **source weight** reflecting how closely its origin exam maps onto the ESAT spec (ESAT=1.0, NSAA-S1=0.95, ENGAA-S1=0.85, TMUA=0.75, NSAA-S2=0.75/0.50). Topic weights within a module vary (e.g. Physics P3 Mechanics gets 45.3% of physics questions because the real exam emphasises it). Difficulty mixes are also module-specific (Physics skews Easy at 42.5%, Chemistry is more balanced).

2. **`coverage_targets.json`** (Opus-produced flat targets) — used as-is if weightings.json is absent.

3. **Taxonomy defaults** — equal split across the 5 ESAT modules (20% each) with a flat 20/50/30 Easy/Medium/Hard difficulty mix.

### Module-level split

**Decision:** `USE_CORPUS_MODULE_MIX = False` at `coverage_tracker.py` line 45 — the cross-module split is deliberately **equal (20% each)** regardless of corpus proportions, because editorial choice is to keep ESAT coverage balanced. The corpus-derived `module_weights` in weightings.json are metadata-only and can be opted into. **Actual corpus proportions are:** Maths1=24.1%, Maths2=13.6%, Physics=30.7%, Chemistry=17.1%, Biology=14.5%.

### Within-module topic spread

**Corpus-weighted.** Each module's topic distribution in `weightings.json` (`topic_weights`) reflects real exam emphasis. For example:
- Physics: P3 (Mechanics) gets 45.3%, P1 (Forces & Equilibrium) gets 11.8%
- Chemistry: C4 (Stoichiometry) gets 22.7%, C15/16/17 (Organic) get <1% each
- Maths1: M1 (Units) gets 43.7%, M6 (Statistics) gets 0.3%

### Spec-only topics

Topics in the ESAT taxonomy with **zero corpus questions** get a small default weight = 1/10 of the average observed topic weight (SPEC_DEFAULT_FRACTION=0.10 at `compute_weightings.py` line 42), then re-normalised. This prevents them from being orphaned entirely.

### How nightly_run decides what to generate next

`nightly_run.py` function `_pick_next_tuple()` (line ~162) sorts all coverage cells by:
1. **fill_ratio** ascending (least-filled first)
2. **shortfall** descending (largest absolute gap)
3. module, topic, difficulty (alphabetical tiebreak)

A `rotation_offset` counter round-robins among tied cells so the alphabetically-first topic doesn't get hammered. Each exhausted cell (3 failed attempts) is added to a `skip` set for the remainder of the batch.

### Gap: generate_and_verify_glm uses UNWEIGHTED shuffle

`generate_and_verify_glm.py` function `_build_work_queue()` (line 970) builds `(spec × difficulty)` tuples and **random.shuffle()**s them with NO weighting or coverage tracking. This means the simpler pipeline treats every topic/difficulty equally regardless of how many questions already exist. Only the `nightly_run.py` path uses the intelligent coverage tracker.

---

## 2. Difficulty Balance

### Structural difficulty scorer (deterministic, NOT LLM self-assessment)

`scripts/difficulty_scorer.py` (ESA-17) scores 0–1 from **structural features** of the question:

| Feature | Weight | Signals |
|---|---|---|
| `step_score` | 0.0–0.30 | Number of solution steps (1=0.0, 5+=0.30) |
| `arith_score` | 0.0–0.15 | Arithmetic density in the worked solution |
| `algebra_score` | 0.0–0.30 | Quadratics (+0.10), simultaneous (+0.12), compound fractions (+0.06), vectors (+0.10), logs (+0.08), trig (+0.05), calculus (+0.12) |
| `reading_score` | 0.0–0.20 | Long stems (>280/+0.06, >520/+0.06), multi-clause (+0.04), I/II/III options (+0.08) |

Band thresholds: 0–0.30=Easy, 0.30–0.55=Medium, 0.55–0.78=Hard, 0.78+=Very Hard.

**Target distribution** (informational only — the orchestrator enforces it): Easy 20%, Medium 50%, Hard 30%, Very Hard 0%.

### Layer 4 structural difficulty in the rebuilt stack

`scripts/quality/structural_difficulty.py` (6-feature scorer) produces a 1–10 **structural** score alongside the LLM's self-assessed `difficulty_score`. It always passes (it's a scorer, not a gate). Features: reasoning_steps, concept_integration, distractor_closeness, context_novelty, trap_presence, option_format.

### Difficulty in the generation prompt

The generator receives an explicit `## TARGET DIFFICULTY` field (Easy/Medium/Hard) and is asked to produce a `difficulty_band` and `difficulty_score` (1–5 integer). The model self-assesses; this is then cross-checked against the structural score at storage time (`nightly_run.py` line ~310 stores both `difficulty_score` and `difficulty_score_structural`).

### Difficulty enforcement via coverage tracker

The coverage tracker maintains per-module difficulty weights from `weightings.json`. These vary by module:
- Physics: Easy 42.5%, Medium 43.6%, Hard 13.9%
- Biology: Easy 26.4%, Medium 50.4%, Hard 23.2%
- Chemistry: Easy 24.2%, Medium 45.6%, Hard 30.2%

The nightly orchestrator picks the under-represented (module, topic, difficulty) cell next, so difficulty balance is **emergent from the coverage targets**, not hardcoded.

### Gap: No post-generation difficulty calibration

If the structural scorer says "Hard" but the coverage target wanted "Easy", the question is still accepted. The only difficulty enforcement is in the **target selection** (what the orchestrator asks for), not in the **output validation** (checking if the result matches). There's no gate that rejects a question for being the wrong difficulty than requested.

---

## 3. Calculator-Friendly vs Non-Calculator Numbers

### Key insight: ESAT is ENTIRELY non-calculator

There is no "calculator section" vs "non-calculator section" — the entire exam is calculator-free. Therefore all questions must use calculator-friendly numbers.

### Mechanism 1: Solution-first protocol (proactive)

`generator_glm.py` SYSTEM_PROMPT (lines 180–250) mandates a **SOLUTION-FIRST** generation protocol:

> "Derive the answer BEFORE the question exists, then build the question around that committed answer."

Phase 0 requires writing `_solution_commit` (full derivation with COMMITTED ANSWER) BEFORE any question text. This structurally ensures the arithmetic is designed to be doable, because the model derives the answer first. `validate_question()` (line 308) **rejects** any question missing this field.

### Mechanism 2: System prompt conventions (proactive)

The system prompt includes **NON-NEGOTIABLE EXAM CONVENTIONS**:
- g = 10 N kg⁻¹ (ALWAYS)
- Angles: {0, 30, 45, 60, 90} degrees only
- Arithmetic: "doable without a calculator — integers, simple fractions, perfect roots, common surds"

### Mechanism 3: Calculability checker (reactive — Layer 1, hard gate)

`scripts/quality/calculability.py` (ESA-55) is the **most ESAT-specific gate**. Two tiers:

**Tier 1 (REJECT):**
- `g != 10` unless 9.81 explicitly given in the stem (`_t1_g_value`)
- Non-standard trig angles without diagram context (`_t1_trig_angles`)
- Values needing >3 significant figures (`_t1_sig_figs`)
- Products of two factors both >15 with no nice structure (`_t1_products`)
- Decimals beyond 2 dp (`_t1_non_terminating`)
- Logarithms of non-exact powers (`_t1_logs`)
- Physical constants used in solution but absent from the stem (`_t1_constants`)

**Tier 2 (WARN only, accepted):**
- Non-perfect square roots (`_t2_roots`)
- Fractions with denominator >12 (`_t2_fractions`)
- Non-SI units (`_t2_non_si_units`)
- Slash units instead of negative indices (`_t2_slash_units`)

### ESA-55 anti-pattern: distractor rationale exclusion

The calculability gate explicitly **strips the "Why the other options are wrong" section** from the worked solution before scanning (`_DISTRACTOR_HEADER_RE` regex, line ~75). This section deliberately contains *wrong* values (e.g. "g = 0.1 instead of g = 10") that would produce false positives.

Similarly, `_correct_path()` (line ~113) scans only the **correct-answer path** (stem + correct option + worked solution) for decimal/sig-fig checks — distractor options are excluded because they carry deliberately unreasonable values.

### Mechanism 4: Revision with calculator-free feedback

In `generate_and_verify_glm.py`, when the calculability gate fails and the question is retryable, the `_revise_question()` function (line ~540) adds an explicit **CALCULATOR-FREE REMINDER** to the revision prompt detailing allowed number types and the specific issues found.

### Research foundation

`calculator-free-research.md` (597 lines) documents the full research basis: which numbers are "safe", which surds students should know, the ESAT Content Specification requirements for mental maths (M2.2–M2.14), and evidence from real ENGAA 2023 past papers.

### Gap: No calc vs non-calc section distinction

There is **no mechanism** to distinguish between "calculator paper" and "non-calculator paper" questions because the ESAT has no such distinction. This is correct for ESAT. However, if the system were ever extended to produce mock papers for exams that DO have this split (e.g. some A-level papers, TMUA), there is no architecture for it.

---

## 4. Question Format Fidelity

### Format enforcement (proactive)

**5 options A–E, exactly 1 correct:**
- System prompt: "Exactly FIVE options (A–E); exactly ONE option must be correct."
- `validate_question()` (line 308): rejects if keys ≠ ["A","B","C","D","E"]
- `validate_question()`: rejects if `correct_answer` is not A–E
- `validate_question()`: rejects if `distractor_analysis` is missing keys for the 4 wrong letters

**JSON-only output:**
- System prompt: "Output ONLY the JSON object. No prose before or after. No ``` fences."
- `parse_question()` strips code fences and extracts JSON via regex

### Distractor analysis requirement

Every generated question must include a `distractor_analysis` dict mapping each wrong letter to a one-line misconception. This is validated by `validate_question()` which rejects if keys are missing or empty.

### Distractor patterns from real corpus (proactive)

Per-topic `distractor_catalogue.<spec_code>.json` files (e.g. `patterns/PHYS.P5/distractor_catalogue.PHYS.P5.json`) contain corpus-extracted distractor types with:
- `distractor_type` — e.g. "Inverse-Volume Confusion", "Energy-Extension Unit/Calculation Error"
- `frequency` — "common", "occasional", "rare"
- `example_question_id` — the real past-paper question where this pattern appears
- `why_effective` — the misconception it exploits
- `generation_strategy` — explicit instructions for the LLM to reproduce this pattern

The user prompt includes: "DISTRACTOR PATTERNS (use at least 2)" with the top 3 patterns injected.

### Few-shot exemplars from real past papers (proactive — ESA-45 Part A)

`scripts/exemplars.py` fetches up to **4 real corpus exemplars** matching the exact (topic, difficulty) cell. Rules:
- Match on `topic_code` section + `difficulty_category` (normalised to Easy/Medium/Hard)
- **Never fall back to a different difficulty** — a cell with zero matches yields zero exemplars
- Presented as "Study these for ESAT style, calibre, and calculator-free arithmetic. Do NOT copy them."

### Style guides from real corpus (proactive)

Per-topic `style_guide.<spec_code>.md` files (e.g. `patterns/PHYS.P5/style_guide.PHYS.P5.md`) are extracted from the corpus by Opus and contain:
- Arithmetic & quantitative constraints (powers of 10, cancelling zeros, fraction types)
- Question structures (format, contexts, data presentation)
- Difficulty calibration (Low/Mid/High band definitions with examples from real questions)

These are injected into the generation prompt as "STYLE GUIDE (Opus-extracted from corpus)".

### Insight scenarios from real corpus (proactive)

Per-topic `insight_scenarios.<spec_code>.json` files provide 3–5 "Aha!" scenarios requiring deep conceptual understanding. The user prompt says: "INSIGHT SCENARIOS (use 1 as the conceptual spine)".

### Reviewer gate (reactive — 4-dimension rubric)

`scripts/quality/reviewer.py` scores each question 1–5 on:
1. **Clarity** — ambiguity, solvability (BLOCKING ≥ 4)
2. **Syllabus** — match to ESAT Content Specification (BLOCKING ≥ 4)
3. **Distractors** — plausibility of wrong options (BLOCKING ≥ 4)
4. **Uniqueness** — advisory only (NOT blocking — because the practice bank deliberately produces standard textbook-style questions)

### Gap: No diagram generation

`has_diagram` and `diagram_description` are generated (the model describes what diagram is needed), but **no actual diagram image is created**. Questions that conceptually require a diagram (circuit, force diagram, graph) are generated with `has_diagram: true` but only a text description exists — students can't see the visual.

---

## 5. Syllabus Alignment

### Taxonomy (proactive)

`esat_taxonomy.json` contains the full ESAT Content Specification with modules → topics → subtopics → skills. This taxonomy drives:
- Pattern extraction (what topics to extract patterns for)
- Coverage tracking (what cells to fill)
- Target distribution (how many questions per topic)

### Per-topic pattern extraction (proactive — ESA-25)

`scripts/pattern-extraction.py` classifies every corpus question to a topic-level spec_code using an LLM classifier (Haiku/GGLM), then for each topic runs a deep extraction call producing the style_guide, distractor_catalogue, and insight_scenarios. The extraction prompt includes:
- Module code, topic name, subtopic codes
- Spec skills sample
- All corpus questions classified under that topic (up to 60)

### Reviewer gate's syllabus dimension (reactive)

The reviewer scores syllabus match 1–5:
- 5: "Plainly within syllabus for the stated module"
- 4: "Within syllabus, borderline topic but reasonable"
- 3: "Borderline; could be argued either way"
- 2: "Likely out of syllabus or off-spec (e.g. g=9.81)"
- 1: "Clearly out of syllabus"

Questions scoring < 4 on syllabus are **rejected**.

### Biology factual judge (reactive, Biology only)

`generate_and_verify_glm.py` `_bio_judge_check_glm()` and `scripts/quality/factual_check.py` (Layer 7) verify factual claims in Biology questions against A-level Biology content. Uses GLM-5.2 with `web_search` tool enabled to check domain-specific facts. Questions with "INCONSISTENT" factual claims are **rejected**.

### Chemistry stoichiometry checker (reactive, Chemistry only)

`scripts/quality/chem_stoich_check.py` parses chemical equations from the worked solution and checks atom balance using RDKit (with a pure-Python fallback). Unbalanced equations are **rejected**.

### Gap: Physics factual checker uses the general factual_check, not a domain-specific one

The `factual_check.py` (Layer 7) applies to chemistry, biology, and physics, but only biology had a **dedicated** gate in the generate_and_verify path. Physics relies on the general factual_check + solver agreement + reviewer syllabus score.

---

## 6. Anti-Patterns / Realism Guards

### Layer 1: Calculability checker
Already detailed in §3. This is the **single most ESAT-specific gate** — 7 Tier-1 reject rules + 4 Tier-2 warn rules.

### Layer 2: SymPy solution verifier
`scripts/quality/sympy_verify.py` — for maths/physics questions with solvable equations, extracts math expressions from the question + worked solution, solves symbolically, and compares to the stated correct answer. If SymPy proves the correct answer is actually wrong → **reject**. Skips (passes) on unparseable/conceptual questions.

### Layer 3: LLM solver (3× majority vote)
`scripts/quality/solver.py` — runs **3 independent solve attempts** at varied temperature. Each sees only the question text and options (never the proposed solution). Results:
- 3/3 agree with key → PASS
- 2/3 agree with key → PASS with warning
- Majority disagrees with key → **REJECT**
- No majority → **REJECT**

In `generate_and_verify_glm.py`, the solver uses GLM-5.2 directly (one attempt, not 3×).

### Layer 5: FAISS dedup + concept cap
`scripts/quality/dedup_check.py`:
1. Embeds the new question text with `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
2. Compares against FAISS IndexFlatIP of ALL existing questions (corpus + previously generated)
3. **Cosine similarity > 0.85 → REJECT** as near-duplicate
4. **Concept cap: max 30 questions per (module, topic, difficulty) cell → REJECT**

The index is built once from the corpus and updated incrementally as questions are accepted (both intra-batch and cross-run).

### Layer 7: Factual check (GLM-5.2 + web_search)
`scripts/quality/factual_check.py` — verifies domain-specific facts in generated questions using GLM-5.2 with web search. Checks each concrete factual claim: confirmed/unconfirmed/incorrect. **Incorrect → reject.**

### g=10 guard (multiple layers)
- System prompt: "Gravitational field strength: g = 10 N kg⁻¹ (ALWAYS)"
- Calculability gate: Tier-1 reject if g ≠ 10 (unless 9.81 explicitly given in stem)
- Revision prompt reinforces this on calculator gate failures

### Self-correction drift prevention
System prompt (Phase 2): "Forbidden: any 'Wait…', 'Let me reconsider…', 'Actually…', 'I'll adjust…' self-correction phrasing."

### Retry-with-feedback loop
`generate_and_verify_glm.py` (line ~490) has a **retry-with-feedback** mechanism: up to 3 revision attempts. On failure, the full verification results are fed back to GLM-5.2 with a revision prompt. Some failures are non-retryable (sympy = wrong math, gate crashes). The revision prompt includes the specific failure reasons and explicit instructions to fix them.

### Gap: No guard against question templates / near-identical structures

The FAISS dedup catches textual near-duplicates, but there's no mechanism to detect **structural clones** — questions that use the same scenario/structure but with different numbers. The concept cap (30 per cell) limits proliferation but doesn't prevent it within the cap.

---

## 7. Weightings and Sampling (Nightly Run Decision Process)

### Full nightly_run.py decision flow

```
1. Load coverage targets from coverage_tracker (weightings.json → flat targets → taxonomy defaults)
2. Count generated questions per (module, topic, difficulty) from DB
3. Compute coverage = fill_ratio for each cell
4. Pick next cell: least fill_ratio → largest shortfall → alphabetical
5. Rotate among tied cells (rotation_offset counter)
6. Generate question for that cell
7. Run all 6 quality gates (Layers 1-5 + 7)
8. If failed and retryable: up to 3 attempts with different seeds
9. If accepted: add to FAISS index, store in DB
10. If cell exhausted (3 failures): skip for remainder of batch
11. Loop until batch_size accepted OR coverage exhausted OR cost ceiling hit
```

### Cost and quota guards

- **Hard cost ceiling:** $5.00 per run (`HARD_COST_CEILING_USD` in nightly_run.py line 37)
- **GLM weekly quota guard:** checks z.ai weekly usage percentage vs elapsed time percentage. If negative headroom, GLM calls are skipped (unless `--ignore-quota`).
- **Per-question budget:** $0.02 (informational, in run_all.py)

### Max attempts per question
3 generation attempts per question cell before moving on (orchestration-review §14.4). Each attempt uses a **deterministic seed** derived from `(topic, difficulty, attempt_n)` so retries produce different questions but are reproducible.

### Gap: generate_and_verify_glm.py has simpler queue

The standalone `generate_and_verify_glm.py` script uses a **random shuffle** of all (spec × difficulty) combos instead of the coverage-weighted selection. It cycles through the entire queue reshuffling each pass. This means when called directly (e.g. for ad-hoc generation), there's no coverage awareness.

---

## Summary: Mechanism Inventory

| # | Mechanism | Type | Location | Focus Area |
|---|-----------|------|----------|-------------|
| 1 | Corpus-weighted topic distribution | Proactive | `compute_weightings.py` | Topic spread |
| 2 | Coverage tracker with fill-ratio picking | Proactive | `coverage_tracker.py` | Topic spread |
| 3 | Per-module difficulty weights from corpus | Proactive | `weightings.json` | Difficulty balance |
| 4 | Structural difficulty scorer (6-feature) | Reactive | `difficulty_scorer.py`, `structural_difficulty.py` | Difficulty balance |
| 5 | Solution-first generation protocol | Proactive | `generator_glm.py` SYSTEM_PROMPT | Calculator-friendly |
| 6 | g=10 convention in system prompt | Proactive | `generator_glm.py` SYSTEM_PROMPT | Calculator-friendly |
| 7 | Standard angles constraint | Proactive | `generator_glm.py` SYSTEM_PROMPT | Calculator-friendly |
| 8 | Calculability checker (7 T1 + 4 T2 rules) | Reactive | `calculability.py` | Calculator-friendly |
| 9 | Distractor rationale exclusion from scans | Reactive | `calculability.py` | Calculator-friendly |
| 10 | 5 options A–E validation | Reactive | `generator_glm.py` validate_question() | Format fidelity |
| 11 | Per-topic distractor catalogues | Proactive | `patterns/*/distractor_catalogue.*.json` | Format fidelity |
| 12 | Few-shot corpus exemplars (4 per generation) | Proactive | `exemplars.py` | Format fidelity |
| 13 | Per-topic style guides | Proactive | `patterns/*/style_guide.*.md` | Format fidelity |
| 14 | Insight scenarios | Proactive | `patterns/*/insight_scenarios.*.json` | Format fidelity |
| 15 | LLM reviewer (4-dim rubric, ≥4 to pass) | Reactive | `reviewer.py` | Format fidelity |
| 16 | ESAT Content Specification taxonomy | Proactive | `esat_taxonomy.json` | Syllabus alignment |
| 17 | Per-topic pattern extraction from corpus | Proactive | `pattern-extraction.py` | Syllabus alignment |
| 18 | Biology factual judge (web search) | Reactive | `factual_check.py`, `bio_judge` | Syllabus alignment |
| 19 | Chemistry stoichiometry checker | Reactive | `chem_stoich_check.py` | Syllabus alignment |
| 20 | Reviewer syllabus dimension | Reactive | `reviewer.py` | Syllabus alignment |
| 21 | FAISS embedding dedup (>0.85 cosine → reject) | Reactive | `dedup_check.py` | Anti-patterns |
| 22 | Concept cap (30 per cell) | Reactive | `dedup_check.py` | Anti-patterns |
| 23 | SymPy solution verifier | Reactive | `sympy_verify.py` | Anti-patterns |
| 24 | 3× solver majority vote | Reactive | `solver.py` | Anti-patterns |
| 25 | GLM factual check with web search | Reactive | `factual_check.py` | Anti-patterns |
| 26 | Retry-with-feedback loop (3 revisions) | Reactive | `generate_and_verify_glm.py` | Anti-patterns |
| 27 | Coverage-weighted nightly orchestration | Proactive | `nightly_run.py` | Weightings |
| 28 | Quota pacing guard | Proactive | `nightly_run.py`, `generator_glm.py` | Weightings |
| 29 | Deterministic seed per (topic, difficulty, attempt) | Proactive | `nightly_run.py` | Weightings |

---

## Identified Gaps

| # | Gap | Severity | Notes |
|---|-----|----------|-------|
| G1 | No post-generation difficulty calibration gate | Medium | A question labelled "Easy" by coverage tracker but scoring "Hard" structurally is still accepted. No gate rejects mismatched difficulty. |
| G2 | generate_and_verify_glm.py uses unweighted shuffle | Low | The standalone script doesn't use coverage tracker — it treats all topics equally. Only nightly_run.py uses intelligent selection. |
| G3 | No diagram generation | High | Questions requiring diagrams (circuits, force diagrams, graphs) are generated with `has_diagram: true` but only text descriptions exist. Students can't see the visual. |
| G4 | No structural clone detection | Low | FAISS catches textual duplicates but not structural clones (same scenario, different numbers). The concept cap (30/cell) limits but doesn't prevent this. |
| G5 | No calc/non-calc paper section distinction | N/A | ESAT is entirely non-calc, so this is correct. Would matter if extended to other exams. |
| G6 | Physics lacks a domain-specific factual gate (like bio_judge) | Low | Physics relies on general factual_check + solver + reviewer. No dedicated physics factual judge exists. |

---

*End of audit.*
