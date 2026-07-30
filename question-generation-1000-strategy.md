# Best Approach for LLM Question Generation to Reach 1,000 Questions

**Prepared:** 2026-07-10
**Author:** Research Agent
**Scope:** Focused recommendation for hitting the 1,000-question target via LLM generation. Builds on (does not duplicate) `question_generation_research.md`, `orchestration-review.md`, `strategy-final-review.md`, `calculator-free-research.md`, `corpus-audit-report.md`, and the GLM-5.2 enrichment trial audit.

---

## 1. Executive Summary

**Recommendation: a hybrid "enrich-first, generate-second" pipeline** using **GLM-5.2 (free tier) as the primary generator** with **Claude Opus 4.8 as the per-topic pattern extractor and final quality judge**. At ~50 questions/night, 1,000 LLM-generated questions are deliverable in **~3–4 weeks of calendar time** for **under $20 in API spend** (and as little as $2 if the GLM-4.5-Air free tier is used for generation).

**Critical strategic insight:** the project already holds **1,687 extracted past-paper questions** (corpus-audit-report.md). After dedup (~38 ENGAA↔NSAA shared-question groups), there are **~1,649 unique real questions** — already more than the 1,000 target. Before generating 1,000 *new* questions, the CEO should decide whether the 1,000-question target is:

- **(A) "1,000 net-new LLM-generated questions"** — pure generation, ignores the existing corpus. Highest cost and risk; only justified if past papers are off-limits for copyright/spec-alignment reasons.
- **(B) "1,000 questions on the website, any source"** — the cheapest path is to dedup + enrich the existing corpus and skip LLM generation almost entirely (corpus alone covers this with margin to spare).
- **(C) "1,000 fresh, original questions, LLM-generated, in addition to the enriched past-paper bank"** — the most defensible interpretation given the parallel `e1ebbb23` goal ("Enrich all 1,687 existing questions with Opus"). **This report assumes (C).**

If interpretation is actually (A) or (B), say so before the build starts — it changes scope by an order of magnitude.

---

## 2. Recommended Approach (Single Pipeline)

### 2.1 Architecture in one paragraph

Two-stage pipeline, custom Python (no LangGraph), cron-driven at night. **Stage 1 (one-time, ~1 day):** Opus 4.8 performs per-topic pattern extraction on the deduplicated corpus → produces a `style_guide.<spec_code>.md`, `distractor_catalogue.<spec_code>.json`, and `insight_scenarios.<spec_code>.json` for each of the ~36 ESAT spec topics (already designed in research §10.2). **Stage 2 (nightly):** a batch generator pulls the next-most-underrepresented topic, generates ~50 question candidates via **GLM-5.2 (free) primary / Haiku 4.5 fallback**, verifies each through a 4-gate quality stack, accepts the survivors, and exports.

### 2.2 Why GLM-5.2 as primary generator (not Haiku 4.5)

The prior research recommended Haiku 4.5 as generator. New evidence from the **GLM-5.2 enrichment trial** (`shared/enriched-output/glm-trial/quality-audit.md`, 2026-07-10) upgrades the recommendation:

- GLM-5.2 is **free via z.ai** for this account (model already wired into the agent runtime)
- Quality audit on the trial batch: 5/5 on math correctness and distractor analysis, 4/5 on classification and difficulty, 5/5 on corpus fidelity
- The trial ran on **enrichment** (a harder task: analyse existing questions). Generation from patterns is easier because the patterns constrain the output.
- Net effect: per-question cost drops from ~$0.0064 (Haiku) to **~$0.0008–$0.0015 (GLM-5.2 free tier, paying only for the Opus judging step)** — a **4–8× cost reduction** vs the prior recommendation

Caveat: GLM-5.2 is not yet validated for *generation from zero* (the trial only validated enrichment). Before committing the full 1,000-question run, a **20-question generation trial** must pass the same 4-dimension audit. If GLM-5.2 fails, fall back to Haiku 4.5 at $0.0064/question — still only ~$6.40 for the whole 1,000.

### 2.3 The 4-gate quality stack (non-negotiable)

Every generated question passes through:

1. **Calculator-free arithmetic checker** (`calculator_check.py`, ~100 LOC) — rejects any question whose worked solution requires evaluating non-perfect-square roots, non-standard trig angles, or 3+ decimal arithmetic. **This is the single most ESAT-specific gate.** Full spec in `orchestration-review.md` Priority #1.
2. **Solver self-consistency** — a second LLM call (Haiku 4.5) independently solves the question; answer must match. Cost: ~$0.0015/Q.
3. **SymPy verifier** (Maths/Physics, ~40–50% coverage per `orchestration-review.md` §7) — symbolic ground-truth check on solvable items. Cost: $0.
4. **Rubric review** (Haiku 4.5, scored 1–5 on clarity / syllabus match / distractor plausibility / uniqueness) — accept ≥4, reject <4. Cost: ~$0.00125/Q.

For **Chemistry**, add a stoichiometry checker (RDKit atom-balance, ~50 LOC). For **Biology**, add an LLM-as-judge factual check against the ESAT Content Specification PDF loaded as context (~$0.0005/Q). These are the two areas the prior reviews flagged as CRITICAL gaps.

### 2.4 Coverage + difficulty orchestration

- **Coverage tracker** picks the next topic from the spec taxonomy based on deficit vs target percentages (research §13.2 — load `coverage_targets.json` produced by Opus, do **not** hardcode).
- **Difficulty balancer** holds a 20/50/30 easy/medium/hard split by always pulling the most under-represented band (research §13.3).
- **Embedding dedup** (FAISS + `all-MiniLM-L6-v2`, threshold 0.85) prevents near-duplicate proliferation (research §13.1). Add a secondary concept-level cap: max N questions per `(module, topic, difficulty, template_id)` tuple.

---

## 3. The Math: How to Hit 1,000

### 3.1 Target allocation across modules

Distribute 1,000 questions proportionally to ESAT exam weight and corpus gaps. Recommended split (derive final numbers from Opus pattern extraction, not this table):

| Module           | Share | Target Qs | Notes                                            |
| ---------------- | ----- | --------- | ------------------------------------------------ |
| Mathematics 1    | 25%   | 250       | Highest student volume; many templates possible  |
| Mathematics 2    | 20%   | 200       | Calculus, further mechanics — harder to generate |
| Physics          | 25%   | 250       | Heaviest diagram need                            |
| Chemistry        | 15%   | 150       | Stoichiometry + RDKit for diagrams               |
| Biology          | 15%   | 150       | Hardest to verify; plan heavier LLM-as-judge use |
| **Total**        | 100%  | **1,000** |                                                  |

### 3.2 Batch sizing and pace

| Parameter                   | Conservative | Aggressive |
| --------------------------- | ------------ | ---------- |
| Batch size (questions/night) | 50           | 150        |
| Expected reject rate         | 15%          | 20%        |
| Net questions/night          | ~43          | ~120       |
| Nights to reach 1,000        | ~24          | ~9         |
| Calendar time                | ~3.5 weeks   | ~1.5 weeks |

**Recommendation: start at 50/night for the first week** (to surface failure modes), **then scale to 100–150/night** once reject rate is under 15%. This puts 1,000 questions in hand within **2–3 weeks of generation start**, with a one-week setup phase before that.

### 3.3 Cost projection (1,000 questions)

Assuming GLM-5.2 free-tier generation + Haiku 4.5 solver/reviewer (Batch API + prompt caching):

| Item                                                  | Cost (USD) |
| ----------------------------------------------------- | ---------- |
| Opus per-topic pattern extraction (one-time, §10.2)   | $6–$8      |
| GLM-5.2 generation calls (free tier)                  | $0         |
| Haiku 4.5 solver verification (1,250 attempts)        | ~$2.00     |
| Haiku 4.5 rubric review (1,250 attempts)              | ~$1.50     |
| SymPy + calculator check                             | $0         |
| Diagram generation (TikZ/Matplotlib, ~40% of Qs)      | ~$1.00     |
| Biology SVG template library (one-time, contractor)   | ~$200.00   |
| **Subtotal (excl. Bio templates)**                    | **$10–$13** |
| **Total incl. Bio templates**                         | **$210–$213** |

If GLM-5.2 generation quality fails the trial and we fall back to Haiku 4.5 generation: add ~$6.40. **Even worst-case total is under $20 of API spend** (excluding one-time Bio template design work, which is optional and reusable).

### 3.4 Throughput ceilings to watch

- **Opus pattern extraction** is the critical-path one-time step (~$7, takes a single day). Generation cannot start until it produces the per-topic config files.
- **TikZ compilation on ARM** (Ampere A1 on Oracle Cloud free tier) — `pdflatex` works but can be slow for batch diagrams. Cache compiled PDFs by source hash (`orchestration-review.md` §3).
- **GLM-5.2 free-tier rate limits** — unstested at batch scale. If rate-limited, switch to GLM-4.5-Air ($0.20/$1.10 MTok, still cheap) or Haiku 4.5.
- **RDKit on ARM64** — verify install works before relying on it; fallback is `chemfig` only for Chemistry diagrams (`orchestration-review.md` §3).

---

## 4. Critical Blockers (must resolve before generation starts)

In priority order, from the prior reviews:

| # | Blocker                                                          | Severity | Effort        | Source                                   |
| - | ---------------------------------------------------------------- | -------- | ------------- | ---------------------------------------- |
| 1 | Calculator-free arithmetic checker                               | 🔴       | ~100 LOC      | orchestration-review §Priority #1        |
| 2 | Chemistry stoichiometry / Biology LLM-as-judge verification      | 🔴       | ~150 LOC      | orchestration-review §Priority #3        |
| 3 | Opus per-topic pattern extraction (produces all config files)    | 🔴       | 1 day + ~$7   | question_generation §10.2                |
| 4 | 20-question GLM-5.2 generation trial + quality audit             | 🔴       | half a day    | NEW (enrichment trial passed; generation unproven) |
| 5 | SQLite/Postgres question-bank schema                             | 🟡       | ~50 LOC DDL   | orchestration-review §Priority #5        |
| 6 | Structural difficulty scorer (not LLM self-assessment)           | 🟡       | ~150 LOC      | orchestration-review §Priority #4        |
| 7 | Embedding dedup on ARM64 verification                            | 🟡       | 1 hr          | orchestration-review §13 note            |
| 8 | g = 10 convention + standard-angle constraint in generation prompt | 🟡     | 1 line        | strategy-final-review Gap #1             |
| 9 | Expert review sampling gate (10%) — manual spot-check cadence    | 🟠       | process       | orchestration-review §Priority #6        |
| 10| Error handling: max 3 retries per question, then discard         | 🟠       | small         | orchestration-review §14.4 finding       |

**Items 1–4 are blockers.** Items 5–10 should land before nightly batches scale past 50/night but can follow the initial trial.

---

## 5. Phased Plan

### Phase 0 — Strategic clarification (this week, CEO decision)
Resolve interpretation (A/B/C above). Confirm 1,000 = "1,000 new LLM-generated, in addition to enriched past-paper bank" — or redirect.

### Phase 1 — Foundation (~1 week)
1. Ingest ESAT Content Specification PDF → `config/spec_taxonomy.json` (already partially done — `shared/esat_taxonomy.json` exists).
2. Run Opus per-topic pattern extraction (~$7, one day) → produces per-topic `style_guide`, `distractor_catalogue`, `insight_scenarios`.
3. Build `calculator_check.py`, `sympy_verifier.py`, `solver.py`, `reviewer.py`, `difficulty_scorer.py`, `chem_stoich_check.py`, `bio_judge.py`.
4. Define DB schema (questions, attempts, reviews, coverage_targets tables).
5. Build `dedup.py` (FAISS + sentence-transformers on ARM64 — verify first).
6. Build Biology SVG template library (parallel workstream, ~$200 contractor, 1 week).

### Phase 2 — Trial (~3 days)
1. Run a **20-question GLM-5.2 generation trial** spanning 5 modules.
2. Run the same 20 questions through Haiku 4.5 for A/B comparison.
3. Audit both batches on the 4 quality dimensions (correctness, distractor quality, classification, difficulty). Decide primary generator. **Go/no-go gate.**

### Phase 3 — Nightly generation (~2–3 weeks)
1. Start at 50 questions/night, cycle modules via coverage tracker.
2. After 1 week of stable <15% reject rate, scale to 100–150/night.
3. Weekly: human spot-check 10% of accepted questions. Recalibrate difficulty scorer if drift observed.
4. Export to web platform once a stable 1,000-questions-ready pool accumulates.

### Phase 4 — Handover (~1 week)
1. Promote 1,000 verified questions to the website question bank.
2. Keep nightly generation running at maintenance rate (~30/night) to refresh and fill coverage gaps over time.
3. Run a final dedup pass against the past-paper corpus to ensure no overlaps.

**Total elapsed: ~4–5 weeks from greenlight to 1,000 delivered questions.**

---

## 6. Key Findings (bulleted)

- **Existing corpus already exceeds 1,000 unique questions** (1,649 after dedup of 1,687 extracted). Pure LLM generation is only needed if interpretation (A) or (C) holds. **CEO must confirm interpretation.**
- **GLM-5.2 should be the primary generator, not Haiku 4.5.** The 2026-07-10 enrichment trial scored GLM-5.2 at 5/5 on math correctness and 5/5 on distractor analysis. Generation is an easier task than enrichment. Cost drops 4–8× vs prior recommendation.
- **Opus 4.8 stays for two roles only:** one-time per-topic pattern extraction (~$7) and optional final-appeal judging. Do not use Opus for bulk generation.
- **Architecture B (Premium Pipeline) from the prior research remains the right shape** — but swap Haiku → GLM-5.2 in the "Question Generator" role.
- **Three CRITICAL blockers exist that the prior reviews flagged but were never built:** calculator-free checker, Chem/Bio verification, and the Opus pattern-extraction run itself. None are coded yet. Generation cannot start cleanly until they are.
- **Cost ceiling is under $20 in API spend** for the full 1,000 questions (worst case, Haiku fallback). The only material cost is ~$200 for one-time Biology SVG template design, which is optional and reusable.
- **Calendar time is ~4–5 weeks** with conservative batch sizing; can be compressed to ~3 weeks if Phase 2 trial passes cleanly and nightly batches scale to 150.
- **Reject rate is the leading indicator.** Target <15%. If the trial rejects >30%, halt and re-extract patterns or switch generator model.
- **ARM64 verification needed** for `sentence-transformers`, `RDKit`, and batch TikZ compilation before relying on them in nightly runs.

---

## 7. Confidence and Gaps

**High confidence:**
- Model selection (GLM-5.2 + Opus, validated by trial)
- Pipeline shape (Architecture B, validated by 3 prior reviews)
- Cost projection (within 20% — pricing tables are verified)
- Coverage/dedup/difficulty mechanics (well-researched, code examples exist)

**Medium confidence:**
- Calendar-time estimate (assumes <15% reject rate; untested at scale)
- Module allocation percentages (real weights should come from Opus extraction, not this report)

**Low confidence / open questions:**
- **GLM-5.2 free-tier rate limits at 50+ calls/night** — untested. Fallback to GLM-4.5-Air ($0.20/$1.10 MTok) or Haiku 4.5 if throttled.
- **GLM-5.2 generation quality from zero** (vs enrichment). Trial only validated enrichment. Phase 2 closes this gap.
- **Whether the 1,000 target means new-generation-only or any-source.** This report assumes (C) — confirm before Phase 1.
- **Biology SVG template design cost** ($200 estimate from prior research; could be higher if contractor rates change).

---

## Sources

All sources are in the `shared/` directory unless external:

1. `shared/question_generation_research.md` — primary 2,789-line research doc (architectures, pricing, QA stack, infinite generation mechanics, cost model)
2. `shared/orchestration-review.md` — cross-reference audit identifying 3 critical blockers (calculator-free checker, Chem/Bio verification, DB schema)
3. `shared/strategy-final-review.md` — final strategy audit, 3 minor gaps identified
4. `shared/strategy-TRIAL-READINESS-REPORT.md` — trial-readiness assessment
5. `shared/question-corpus-final-check.md` — 1,687-question corpus audit, 38 dup groups
6. `shared/calculator-free-research.md` — full basis for the calculator-free checker (g=10, standard angles, mental-arithmetic rules)
7. `shared/enriched-output/glm-trial/quality-audit.md` — 2026-07-10 GLM-5.2 trial audit (5/5 math correctness, 5/5 distractor analysis)
8. `shared/esat_format_research.md` — ESAT format spec (27 Qs/module, 5 options A–E, no calculator, g=10)
9. `shared/esat_taxonomy.json` — per-module spec taxonomy (already extracted)
10. External: [ESAT Content Specification PDF](https://uat-wp.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/04/30103004/ESAT_Content_Specification_April2025.pdf) — authoritative syllabus
11. External: [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [z.ai pricing](https://docs.z.ai/guides/overview/pricing) — verified 2026-07

---

*End of report. Ready for CEO review.*
