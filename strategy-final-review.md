# Final Review: "Opus Calls Alternative — GLM-5.2 Hybrid Strategy"

**Reviewer:** Subagent (automated cross-reference audit)
**Date:** 2026-07-08
**Document reviewed:** `/home/ubuntu/dashboard/reports/opus-calls-alternative.html`
**Cross-referenced against:** 14 source documents (see below)

---

## Verdict: ✅ READY FOR TRIAL — with 3 minor gaps to address post-trial

The hybrid strategy document is **well-specified, internally consistent, and directly implementable**. It correctly focuses on the immediate need: replacing Opus calls for text-only question enrichment with free GLM-5.2. The prompts, output format, routing logic, test plan, and cost analysis are all clear enough for a coding agent to build the trial pipeline.

Below are the findings in detail.

---

## 1. Coverage of Previous Research

### ✅ Fully Incorporated

| Source Document | Key Insight | Incorporated? |
|---|---|---|
| `question_generation_research.md` | GLM-5.2 pricing ($1.40/$4.40 MTok) and z.ai free tier availability | ✅ Yes — states GLM-5.2 is free via z.ai |
| `question_generation_research.md` | Architecture B recommendation (Opus for analysis, cheaper model for generation) | ✅ Yes — GLM-5.2 handles bulk text, Opus retained for diagrams |
| `question_generation_research.md` | Prompt caching for Opus (90% cache read savings, 5-min TTL) | ✅ Yes — full Section 4 with pricing tables |
| `question_generation_research.md` | Batch API 50% discount for Opus | ✅ Yes — mentioned in cost tables |
| `esat_format_research.md` | 5-option MCQ format (A–E), 27 Qs per module, 40-min time limit | ✅ Yes — test plan references text-only questions |
| `esat_format_research.md` | No calculator allowed, g = 10 N/kg | ⚠️ Not explicitly mentioned (see Gap #1 below) |
| `esat_format_research.md` | Scoring 1.0–9.0, no negative marking | Not relevant — this doc is about enrichment, not generation |
| `calculator-free-research.md` | g = 10 convention, standard angles only, mental arithmetic constraints | ⚠️ Not explicitly mentioned (see Gap #1 below) |
| `contradiction-analysis.md` | Calculator-free check as critical gap | ⚠️ Partially — the enrichment task doesn't *generate* numbers, so this is less critical, but still relevant for verification |
| `contradiction-analysis.md` | Expert review sampling gate (10%) | Not directly relevant — trial is 3 questions, not production generation |
| `contradiction-analysis.md` | Custom Python orchestrator, no LangGraph | ✅ Yes — architecture implies custom Python pipeline |
| `contradiction-analysis.md` | LLM self-assessment of difficulty is unreliable | ✅ Yes — the strategy includes difficulty rating as output but evaluation is done via human A/B comparison, not trusting the LLM rating |
| `orchestration-review.md` | Calculator-free checker as Top Priority #1 | ⚠️ Less critical here (enrichment, not generation) but relevant for output validation |
| `orchestration-review.md` | Database schema needed for coding agent | Not directly relevant — trial is 3 questions, schema comes later |
| `orchestration-review.md` | SymPy coverage is 40–50%, not 70% | Not relevant — no SymPy in this pipeline |
| `DESIGN_PHILOSOPHY.md` | Markdown + LaTeX output format | ✅ Yes — central design decision, fully specified |
| `design.md` | Precision instrument philosophy | ✅ Implicitly reflected in the structured output format |
| `esat_taxonomy.json` / `esat_taxonomy_summary.txt` | Per-module taxonomy with content codes | ✅ Yes — `{esat_taxonomy_for_module}` placeholder in prompts, module mapping table in Section 8 |
| `aqg-research-esat-question-generation.html` | ReQUESTA framework insights on distractor quality | ✅ Yes — distractor analysis is a key output section in both prompts |
| `opus-enrichment-pipeline.html` | Original Opus enrichment pipeline design | ✅ Yes — this is the document being superseded/refined |
| `esat-implementation-plan.html` | Phase structure and OCR pipeline | ✅ Yes — mentions OCR extraction as the source of `has_diagram` classification |
| `esat-question-format-validation.html` | Question format validation findings | ✅ Consistent — strategy acknowledges variable option counts (4–8) |
| `nsaa-engaa-esat-overlap-analysis.html` | TMUA/ENGAA/NSAA past paper mapping | ✅ Yes — Section 8 provides full past paper to module mapping |

---

## 2. Specific Gaps Identified

### Gap #1 (Minor): No explicit g = 10 N/kg or calculator-free constraint in prompts

**What's missing:** The prompts don't instruct the model to use g = 10 (not 9.81) when writing physics worked solutions. The `calculator-free-research.md` establishes this as an ESAT convention. Similarly, there's no instruction to use standard angles (0°, 30°, 45°, 60°, 90°) only.

**Impact on trial:** Low. The enrichment task analyses *existing* questions — the numbers are already in the question. If a past paper question says g = 10, the model will use g = 10. If the model writes g = 9.81 in a worked solution for a question that implies g = 10, that's a quality issue the A/B comparison would catch.

**Recommendation:** Add a brief instruction to both prompts: *"Where the question implies a value of g, use g = 10 m s⁻² (the ESAT convention). Use only standard trig angles (0°, 30°, 45°, 60°, 90°) unless the question specifies otherwise."* This takes one line and prevents a known failure mode.

### Gap #2 (Minor): "≥90% of Opus quality" threshold is vague

**What's missing:** The test plan (Section 6) says "GLM-5.2 output quality ≥90% of Opus 4.8 quality" but doesn't define how this percentage is calculated. Is it an average across all 4 dimensions? A minimum per-dimension? Evaluated by whom (human, LLM-as-judge, rubric)?

**Impact on trial:** Low-Medium. For 3 questions, a human can make a holistic judgment. But for scaling to the full corpus, a more precise evaluation rubric is needed.

**Recommendation:** For the trial, state: *"Quality is assessed holistically by the reviewer. If GLM-5.2 produces a correct worked solution with proper LaTeX, plausible distractor explanations, and reasonable topic classification for all 3 questions, the threshold is met. Specific failures (wrong calculation, hallucinated content code, non-standard LaTeX) are documented as failure modes."* For the full corpus scale-up, develop a scored rubric (the contradiction analysis and orchestration review both recommend this).

### Gap #3 (Info): No mention of NSAA Section 2 advanced topic filtering

**What's missing:** The task briefing asked about TMUA filtering rules and NSAA S2 advanced topic filtering. The strategy document doesn't explicitly call out filtering rules for which questions are included/excluded from enrichment. Section 8 maps NSAA S2 to the taxonomy but doesn't say "only include questions within the current ESAT spec."

**Impact:** Negligible for the trial. For full corpus enrichment, the coding agent will need to know: should questions testing content *outside* the current ESAT Content Specification be enriched (yes, they're still valid practice) or excluded (no, they're irrelevant)?

**Recommendation:** This is a filtering decision, not a strategy document gap. Add a note to the module mapping section: *"All questions from mapped past papers are enriched regardless of whether their specific content falls within the current ESAT specification. The enrichment pipeline does not filter by topical relevance — only by diagram status."* Or the opposite if filtering is desired. State it explicitly.

---

## 3. Pipeline Specification Assessment

### 3-Stage Pipeline: Fully Specified ✅

The document describes a clear 2-branch pipeline (not 3-stage — see note below):

1. **Routing:** `has_diagram` check (from OCR, not LLM) → text or diagram branch
2. **Enrichment:** GLM-5.2 or Opus 4.8 processes the question using the appropriate prompt
3. **Output:** Identical Markdown + LaTeX schema from both branches, merged into enriched corpus

**Note:** The task briefing refers to a "3-stage pipeline (Opus analysis → GLM generation → verification)." The actual document describes a **2-model parallel enrichment** approach, not a sequential 3-stage pipeline. This is a **simplification** from the original enrichment pipeline concept — it removes the separate Opus analysis step and has GLM-5.2 do the full enrichment directly. This is fine for the trial (simpler, faster) but the original 3-stage concept had Opus doing deep analysis first, which might produce higher quality than having GLM-5.2 do everything solo.

**Assessment:** The 2-model parallel approach is **correct for a trial** — it tests whether GLM-5.2 can do the full enrichment alone. If quality is insufficient, the fallback is to add back the Opus analysis stage (3-stage). This is a good trial design.

### TMUA Filtering Rules: Present ✅

Section 8 maps TMUA P1 → Maths 1, TMUA P2 → Maths 2 with question counts. No explicit filtering rules beyond the module mapping, which is sufficient.

### NSAA S2 Advanced Topic Filtering: Partially Present ⚠️

Section 8 maps NSAA S2 to single-subject taxonomy. No filtering of advanced/out-of-spec topics. See Gap #3 above.

---

## 4. Trial Parameters Assessment

**Trial spec (Section 6):**
- 3 text-only questions ✅
- Varying difficulty (one straightforward, one multi-step, one conceptual) ✅
- Both GLM-5.2 and Opus 4.8 process same 3 questions ✅
- 4-dimension quality evaluation ✅
- ≥90% threshold ✅ (with minor vagueness — see Gap #2)
- Go/no-go decision before scaling ✅
- Fallback: route specific sub-types back to Opus ✅

**Assessment:** Trial parameters are clear enough to execute immediately. A coding agent knows exactly what to build and what the success criteria are.

---

## 5. Output Format Assessment for Coding Agent

**What's specified:**
- ✅ Markdown + LaTeX output format
- ✅ 5 sections: Worked Solution, Distractor Analysis, Classification, Difficulty Rating, Diagram Descriptions
- ✅ Classification fields: Module, Subtopic, Content Code, Question Type
- ✅ Difficulty: 1-10 scale with justification
- ✅ LaTeX conventions: `$...$` inline, `$$...$$` display
- ✅ Diagram markers: `[DIAGRAM n]` with max 4 per question
- ✅ Self-contained text requirement (solution works without diagrams)
- ✅ Example output provided

**What's missing but needed for coding agent:**
- ⚠️ No JSON output schema — the output is Markdown, but the coding agent needs to know if they should parse the Markdown into structured fields (JSON) or store raw Markdown. The orchestration review provided a SQL schema; the coding agent should use that.
- ⚠️ No error handling for malformed LLM output — what if GLM-5.2 returns output missing a section? The strategy should mention: *"If any required section is missing from the output, flag the question for re-processing."*

**Assessment:** 90% specified. The two missing items above are implementation details that the coding agent can infer from the orchestration review's database schema. Not blockers.

---

## 6. Risk Assessment

The document identifies 5 risks (1 high, 3 medium, 1 low). All are reasonable and properly mitigated. One additional risk not mentioned:

- **Additional risk (medium):** GLM-5.2 may produce content codes that don't exist in the taxonomy (hallucinated codes). Mitigation: validate all output content codes against the loaded taxonomy JSON; flag unknown codes for review.

---

## Summary

| Check | Status |
|---|---|
| Incorporates findings from all previous research? | ✅ Yes (with 1 minor omission — g=10 convention) |
| Missing important insights/constraints/decisions? | ⚠️ 3 minor gaps (g=10, quality threshold definition, NSAA S2 filtering) |
| Pipeline fully specified with no ambiguities? | ✅ Yes — clear 2-model parallel architecture |
| TMUA filtering rules documented? | ✅ Yes (Section 8) |
| NSAA S2 advanced topic filtering documented? | ⚠️ Partial — mapping exists, no filtering rules |
| Trial parameters clearly defined? | ✅ Yes — 3 questions, A/B comparison, 4 dimensions, ≥90% |
| Output format sufficient for coding agent? | ✅ 90% — Markdown structure + example provided; JSON parsing is implicit |

**Overall assessment: The document is ready for the coding agent to implement the trial.** The 3 gaps identified are minor and can be addressed as inline additions (a few sentences each) without restructuring the document. None are blockers for the 3-question trial.

**Recommended action:** Proceed with trial implementation. Address Gap #1 (g=10 instruction in prompts) before sending the first prompt to GLM-5.2. Address Gap #2 (quality evaluation detail) before evaluating results. Address Gap #3 (filtering decision) before scaling to full corpus.
