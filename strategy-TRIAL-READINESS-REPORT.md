# Trial Readiness Report — GLM-5.2 Hybrid Strategy

**Prepared:** 2026-07-08 (Subagent cross-reference audit)
**Document reviewed:** `strategy-final-review.md` (the final strategy/review document)
**Cross-referenced against:**
1. `question_generation_research.md` (2,790 lines — model pricing, architectures, 3-stage pipeline, prompt templates, weightings, distractor generation)
2. `orchestration-review.md` (Orchestration plan review — critical gaps, calculator-free checker, DB schema, Chem/Bio verification)
3. `esat_format_research.md` (ESAT format spec — 27 Qs/module, 5 options A–E, 40 min, no calculator, g=10)
4. `corpus/format-manifest.json` (field definitions — 52 corpus files across ENGAA/NSAA/TMUA)

---

## 1. What the Strategy Covers

The final review document (`strategy-final-review.md`) is **itself a comprehensive audit** of the hybrid strategy. It contains:

- **Verdict:** ✅ READY FOR TRIAL with 3 minor gaps
- **Coverage matrix:** 18 source documents cross-referenced against key insights
- **Pipeline specification:** 2-model parallel architecture (GLM-5.2 for text enrichment, Opus 4.8 for diagram questions)
- **Trial parameters:** 3 text-only questions, A/B comparison (GLM-5.2 vs Opus 4.8), 4-dimension quality evaluation, ≥90% threshold
- **Output format:** Markdown + LaTeX, 5 sections (Worked Solution, Distractor Analysis, Classification, Difficulty Rating, Diagram Descriptions)
- **Risk assessment:** 5 identified risks (1 high, 3 medium, 1 low)
- **Module mapping:** Section 8 maps TMUA P1/P2 and NSAA S2 to ESAT modules

### Key Design Decisions Documented
| Decision | Status |
|---|---|
| GLM-5.2 replaces Opus for text-only question enrichment | ✅ Clear |
| Opus retained for diagram questions | ✅ Clear |
| Routing based on `has_diagram` (from OCR, not LLM) | ✅ Clear |
| Markdown + LaTeX output format (not JSON) | ✅ Clear |
| Classification fields: Module, Subtopic, Content Code, Question Type | ✅ Clear |
| Cost analysis with prompt caching and Batch API discounts | ✅ Clear |
| Source relevance weighting for corpus sources | ✅ Clear (Section 10.2.7 of research) |

---

## 2. Items from Earlier Documents NOT in the Final Strategy

### 2.1 Missing from the Trial Protocol (Should Address Before Trial)

| # | Item | Source | Impact | Action |
|---|---|---|---|---|
| G1 | **No g = 10 N/kg instruction in prompts** | `esat_format_research.md`, `orchestration-review.md` | Low for trial (enrichment analyses existing questions), but prevents a known failure mode | Add to both prompts: *"Where the question implies a value of g, use g = 10 m s⁻². Use only standard trig angles (0°, 30°, 45°, 60°, 90°)."* |
| G2 | **Quality threshold ≥90% is undefined** | `orchestration-review.md` (rubric recommendation) | Medium — 3 questions allows holistic judgment, but scaling needs precision | For trial: state "holistic reviewer judgment." For scale-up: develop scored rubric. |
| G3 | **No explicit TMUA non-calculus filtering rule** | `esat_format_research.md`, `question_generation_research.md` §10.2.7 | Low — strategy maps TMUA P1→Maths1, P2→Maths2, but TMUA P2 has calculus questions. Maths 2 includes calculus in ESAT spec, so this is actually fine. **No gap.** | N/A — TMUA P2 calculus maps correctly to Maths 2 |
| G4 | **No explicit NSAA S2 advanced topic filtering decision** | `question_generation_research.md` source weights (NSAA S2 weighted 0.50–0.70) | Low for trial. For scale-up: need explicit "enrich all questions" vs "filter to ESAT spec only" | Add a decision statement to Section 8 mapping |

### 2.2 Important from Research Doc But Not in Final Strategy (Post-Trial Concerns)

| # | Item | Source | Why It Matters |
|---|---|---|---|
| R1 | **3-stage pipeline design** (Haiku classification → Opus per-topic extraction → generation) | `question_generation_research.md` §10.2 | The final strategy uses a simpler 2-model parallel approach for the trial. The 3-stage pipeline is the production plan. The trial intentionally tests whether GLM-5.2 can do full enrichment solo. **This is fine — the trial is validating the simpler approach first.** |
| R2 | **Source relevance weights** (NSAA S1=0.95, ENGAA S1=0.85, TMUA=0.75, NSAA S2=0.50–0.70) | `question_generation_research.md` §10.2.7 | Essential for full corpus enrichment. Not needed for 3-question trial. |
| R3 | **Computational distractor generation** (solution-first generation, error transforms, SymPy) | `question_generation_research.md` §7.2, `orchestration-review.md` Priority #8 | Not relevant to trial (enrichment, not generation). Critical for full question generation pipeline. |
| R4 | **Calculator-free arithmetic checker** (`calculator_check.py`) | `orchestration-review.md` Priority #1 (CRITICAL) | Not relevant to trial (enrichment analyses existing questions). **Critical blocker for generation pipeline.** |
| R5 | **Chemistry/Biology verification strategy** | `orchestration-review.md` Priority #3 (CRITICAL) | Not relevant to trial. Critical for full pipeline — SymPy only covers ~40–50% of Maths/Physics. |
| R6 | **Database schema** | `orchestration-review.md` Priority #5 | Not needed for trial (3 questions, can be ad-hoc). Needed for scale-up. |
| R7 | **Difficulty calibration** (structural scorer, not LLM self-assessment) | `orchestration-review.md` Priority #4, `question_generation_research.md` §13.3 | Trial uses human comparison, which is fine. Scale-up needs automated scoring. |
| R8 | **Expert review sampling gate (10%)** | `orchestration-review.md` Priority #6 | Not relevant to trial. Needed for production. |
| R9 | **Error handling / retry strategy** | `orchestration-review.md` Priority #9 | Not critical for 3-question trial. Essential for batch processing. |
| R10 | **SymPy coverage is 40–50%, not 70%** | `orchestration-review.md` Section 7 finding | Corrects an overoptimistic claim in the research doc. Important for realistic cost/verification planning. |

---

## 3. Trial Readiness Assessment

### Protocol Clarity: ✅ CLEAR ENOUGH TO EXECUTE

The trial protocol (Section 6 of the final review) is well-defined:

| Parameter | Specified? | Detail |
|---|---|---|
| Number of questions | ✅ | 3 text-only questions |
| Question selection | ✅ | Varying difficulty: 1 straightforward, 1 multi-step, 1 conceptual |
| Models to compare | ✅ | GLM-5.2 vs Opus 4.8 |
| Prompt templates | ✅ | Both specified with placeholders, example output, LaTeX conventions |
| Output format | ✅ | Markdown + LaTeX, 5 sections, example provided |
| Evaluation dimensions | ✅ | 4 dimensions (implied: correctness, LaTeX quality, distractor analysis, classification) |
| Success threshold | ⚠️ | "≥90% of Opus quality" — vague but workable for 3 questions |
| Go/no-go decision | ✅ | Before scaling |
| Fallback plan | ✅ | Route specific sub-types back to Opus |

### What a Coding Agent Needs to Build the Trial

1. **Select 3 questions** from the corpus (text-only, varying difficulty) — the corpus files are in `corpus/` directory with clean extractions per `format-manifest.json`
2. **Write the GLM-5.2 API call** using the prompt template from the strategy document
3. **Write the Opus 4.8 API call** using the same prompt template
4. **Run both models** on the same 3 questions
5. **Present outputs side-by-side** for human comparison

This is straightforward. No database, no pipeline, no verification tools needed — just raw API calls and manual output comparison.

### One Ambiguity to Resolve

The final review notes that the document describes a **"2-model parallel enrichment"** approach (GLM-5.2 and Opus each do the full enrichment independently), while the task briefing references a **"3-stage pipeline (Opus analysis → GLM generation → verification)"**. These are different architectures:

- **2-model parallel:** Both models do the same job independently; compare outputs
- **3-stage sequential:** Opus analyses first, GLM generates from Opus analysis, then verification

**The 2-model parallel approach is the correct trial design** — it tests whether GLM-5.2 can match Opus when doing the full enrichment alone. If it can't, the 3-stage approach (where Opus does analysis first, then GLM generates from a richer prompt) becomes the fallback. This is a good trial design but should be explicitly stated.

---

## 4. Gaps and Risks

### Pre-Trial (Must Address)

| Gap | Severity | Fix Effort |
|---|---|---|
| **G1: g = 10 instruction in prompts** | Low | 1 sentence added to each prompt template |
| **G4: NSAA S2 filtering decision** | Low | 1 sentence added to Section 8 |

### Post-Trial (Before Scale-Up)

| Gap | Severity | Fix Effort |
|---|---|---|
| R4: Calculator-free checker | 🔴 CRITICAL | New Python module (~100 lines) |
| R5: Chem/Bio verification | 🔴 CRITICAL | LLM-as-judge + RDKit stoichiometry |
| R6: Database schema | 🟡 HIGH | SQL DDL (~50 lines) |
| R7: Difficulty scoring | 🟡 HIGH | Structural scorer (~150 lines) |
| R8: Expert review gate | 🟡 HIGH | Sampling logic + review workflow |
| R9: Error handling | 🟠 MEDIUM | Retry/backoff logic in orchestrator |
| R10: SymPy coverage correction | 🟠 MEDIUM | Update documentation |
| R1: 3-stage production pipeline | 🟠 MEDIUM | Already designed in research doc — implement after trial |

### Risk Not Identified in Strategy

- **GLM-5.2 hallucinated content codes:** GLM-5.2 may produce taxonomy codes that don't exist in the ESAT Content Specification. Mitigation: validate all output content codes against the loaded taxonomy JSON. Flag unknown codes for review.

---

## 5. Verdict

**✅ TRIAL-READY** with 2 trivial pre-trial additions (g=10 instruction, NSAA S2 filtering statement).

The strategy document is a thorough, well-specified audit that correctly identifies the 3 minor gaps, accurately maps the 2-model parallel architecture, and provides enough detail for a coding agent to implement the 3-question trial immediately.

**The gap between "trial ready" and "production ready" is significant** — the orchestration review identifies 3 critical blockers (calculator-free checker, Chem/Bio verification, DB schema) and several high-priority items that must be built before the full corpus enrichment pipeline can run. But for the purpose of this trial (3 questions, manual comparison), none of those blockers apply.

**Recommended next step:** Add the g=10 instruction to prompts, state the NSAA S2 filtering decision, then proceed to trial execution.

---

*Report prepared: 2026-07-08*
*Reviewer: Subagent (automated cross-reference audit)*
