# Contradiction Analysis: AQG Research Report vs. Current Orchestration Plan

**Date:** 28 June 2026
**Documents compared:**
- **Research:** `aqg-research-esat-question-generation.html` (AQG/ReQUESTA deep dive)
- **Orchestration:** `question-generation-orchestration-brief.html` (v3.1) + `esat-implementation-plan.html` (v2.0)

---

## Methodology

I compared every architectural decision in both documents. Below are the **genuine contradictions** — where the two documents recommend different approaches to the same problem. I filtered out cases where one document simply provides more detail than the other on an agreed approach.

---

## Contradiction #1: Primary LLM Model

| | Research Report | Orchestration Plan |
|---|---|---|
| **Recommendation** | GPT-5 as primary, Claude Sonnet 4 for conceptual/scenario | Haiku 4.5 for T1/T2, Sonnet 4.6 for T3, Opus 4.8 for T4 |
| **Rationale** | GPT-5 has strongest overall reasoning and is the ReQUESTA baseline model. Sonnet 4 has highest Bloom's alignment for higher-order items. | Cost optimisation — start cheap, escalate. Haiku Batch at $0.003/question vs Sonnet at $0.018/question. |

**My recommendation: Go with the Orchestration Plan (Haiku → Sonnet → Opus tiered routing).**

The research report recommends GPT-5 because it was the baseline used in the ReQUESTA study, not because of a head-to-head comparison against Claude models for STEM MCQ generation. The orchestration plan's tiered routing is more cost-efficient and includes adaptive re-routing based on observed performance per model per sub-topic. The research report's own key insight from ReQUESTA is that "workflow design matters more than model choice" — which supports using cheaper models in a good pipeline over a single expensive model.

The one caveat: if GPT-5 genuinely outperforms Claude models on physics/math reasoning (as the research suggests), we should benchmark GPT-5 against Sonnet 4.6 on a 50-question test batch before committing. But the default should be the orchestration plan's tiered approach until evidence warrants a switch.

---

## Contradiction #2: Orchestration Framework

| | Research Report | Orchestration Plan |
|---|---|---|
| **Recommendation** | LangGraph (or custom Python) for agentic workflow orchestration | Custom Python orchestrator with no framework dependency |
| **Rationale** | LangGraph provides built-in state management, agent communication, and retry semantics that match the ReQUESTA-style multi-agent decomposition. | The orchestrator is a dispatcher + feedback loop, not a conversational agent. It doesn't need agent-to-agent communication. A custom Python module is simpler, more debuggable, and avoids a framework dependency. |

**My recommendation: Go with the Orchestration Plan (custom Python, no LangGraph).**

The orchestration plan is right about this. The pipeline is not a true multi-agent system where agents converse and negotiate. It's a pipeline: select → generate → verify → refine → store. Each stage is a function call, not an agent. LangGraph adds complexity and a dependency for no architectural benefit. The ReQUESTA framework's "multi-agent" decomposition maps cleanly to separate Python functions/classes in a pipeline.

If we later add genuine agent autonomy (e.g., an agent that decides to regenerate vs. edit vs. escalate on its own), LangGraph becomes more relevant. But for v1, custom Python is the right call.

---

## Contradiction #3: Difficulty Calibration — When and How

| | Research Report | Orchestration Plan |
|---|---|---|
| **Recommendation** | Tiered approach: (1) structural scoring → (2) expert rating sample → (3) IRT calibration once student data exists. SMART-style simulated students for pre-deployment estimates. | Difficulty set at generation time by the template/directive (easy/medium/hard target). No pre-deployment difficulty calibration beyond the LLM's self-assessment. IRT is mentioned as a "future" long-loop feedback mechanism. |
| **Rationale** | LLMs are unreliable at self-assessing difficulty. Structural features (step count, distractor closeness, topic complexity) provide better estimates. Simulated student models can predict difficulty without field data. | The orchestrator assigns a target difficulty band and trusts the LLM + template parameters to hit it. Post-hoc IRT calibration happens only after student data accumulates. |

**My recommendation: Adopt the Research Report's tiered approach, but keep it lightweight for v1.**

This is a real gap in the orchestration plan. Relying on LLM self-assessment for difficulty is unreliable — research consistently shows LLMs are poor judges of question difficulty. The orchestration plan should add a **structural difficulty scoring** step after verification:

1. Score each accepted question on structural features (reasoning steps, concept integration count, distractor closeness, presence of traps).
2. Compare against the target difficulty band from the directive.
3. Flag mismatches for reclassification or regeneration.

Skip the SMART simulated student model for v1 (too complex to build initially). Skip expert rating for every question (too expensive). But do add the structural scoring layer — it's cheap, deterministic, and meaningfully better than LLM self-assessment alone.

---

## Contradiction #4: Expert Review Sampling Rate

| | Research Report | Orchestration Plan |
|---|---|---|
| **Recommendation** | Expert review of a **random sample** of generated questions, with a "Turing test" filter where experts classify as human vs. AI. Cost: ~$2-5/question for the reviewed sample. | No expert review step in the pipeline. Human spot-check is mentioned only in the **corpus ingestion** phase (reviewing 10-20% of classified past papers, not generated questions). |
| **Rationale** | Without human expert eyes on generated questions, quality issues (AI tells, subtle errors, poor distractors) will go undetected. The Turing test filter catches authenticity problems before they reach students. | The pipeline's automated verification (SymPy + quality rubric + FAISS dedup) is treated as sufficient. Budget is tightly controlled via the £5/day circuit breaker. |

**My recommendation: Adopt the Research Report's position — add expert review as a sampling gate.**

This is the orchestration plan's biggest blind spot. Automated verification catches mathematical errors and format issues, but it cannot catch:
- Subtle conceptual errors in physics/chemistry/biology
- AI writing tells (distractor length cues, repetitive sentence structures)
- Questions that are technically correct but pedagogically poor
- Missing "Cambridge voice" — the specific style of real ESAT questions

**Recommended implementation:** Sample 10% of accepted questions for expert review during Phase 4 (test batch) and the first month of Phase 5 (production). After quality stabilises, reduce to 5%. Budget: at ~$2-5/question and a 10% sample rate, reviewing 500 questions from a 5,000-question bank costs $1,000-2,500. This is significant but essential for the stated goal of "fooling a Cambridge examiner."

If budget is a concern, prioritise expert review for Biology and Chemistry (where automated verification is weakest) and for hard-difficulty Physics questions (where the "aha!" factor matters most).

---

## Contradiction #5: Distractor Generation Method

| | Research Report | Orchestration Plan |
|---|---|---|
| **Recommendation** | Multi-method pipeline: (1) misconception-based generation from error taxonomy, (2) computational error transforms for calculation questions, (3) LLM-generated + filtered for conceptual questions, (4) systematic statement-flipping for multi-statement maths. | Template specifies `distractor_strategies` as a list of error descriptions (e.g., "uses sin instead of cos"). LLM generates distractors following these strategies. Verification checks distractors are incorrect via SymPy. No dedicated distractor refinement stage. |
| **Rationale** | Distractor quality is the single biggest differentiator between AI and human-authored questions (DI 0.32 vs 0.48). A dedicated refinement stage is essential. Multiple generation methods are needed because different question types need different distractor strategies. | The template + LLM approach is simpler and built into the generation prompt. SymPy verifies distractors are wrong. Adding a separate refinement stage adds cost and complexity. |

**My recommendation: Hybrid — adopt the Research Report's computational distractor generation for calculation questions, add a lightweight LLM-as-judge refinement step, but don't build the full multi-method pipeline yet.**

The orchestration plan's approach (template strategies + LLM generation + SymPy verification) is a reasonable v1. But it has a gap: no quality check on distractor *plausibility* — only on correctness (are they wrong?) not quality (are they plausibly tempting?).

**Recommended additions to the orchestration plan:**

1. **Computational distractor generation** for calculation questions: Instead of asking the LLM to generate distractors, programmatically apply error transforms (forget to square, use diameter instead of radius, swap sin/cos) to produce deterministic, diagnostic distractors. This is cheaper, more reliable, and produces better discrimination.

2. **LLM-as-judge distractor filter**: After generation, run a cheap Haiku pass that evaluates: "Are these 4 distractors plausible? Do they correspond to identifiable errors? Is the correct answer not consistently longer?" Reject and regenerate if the filter fails.

3. **Keep the misconception-based strategies in templates** as the orchestration plan specifies — but use them to guide *computational* generation where possible, not just LLM generation.

---

## Contradiction #6: Chain-of-Thought Generation Order

| | Research Report | Orchestration Plan |
|---|---|---|
| **Recommendation** | CoT approach: generate the **worked solution first**, then construct the question around it. This ensures solvability and verifiability. | Standard approach: generate the **question first** (stem + options + answer), then verify via SymPy. The worked solution is generated as part of the output but not used to constrain generation. |
| **Rationale** | Generating the solution first means the question is guaranteed solvable with clean numbers. The answer and distractors are derived from the solution, not the other way around. | The standard approach is more natural for LLMs (they're trained on question→answer, not answer→question). SymPy verification catches solvability issues post-hoc. |

**My recommendation: Adopt the Research Report's CoT approach for calculation-heavy questions.**

This is a meaningful improvement. For maths and physics calculation questions, generating the worked solution first and then constructing the question around it has two advantages:

1. **Guaranteed clean numbers**: If you solve "v² = u² + 2as" with s=10, a=5, u=0, you get v=10 (clean). If you pick v first and work backwards, you may get s=10.4 (ugly).
2. **Natural distractor generation**: The worked solution reveals which intermediate steps a student could get wrong, directly producing diagnostic distractors.

For conceptual/scenario questions where there's no calculation chain, the standard approach is fine. But for the ~50% of questions that are calculation-based, CoT generation should be the default.

**Implementation**: Add a `generation_strategy` field to templates: `solution_first` (for calculation questions) or `question_first` (for conceptual questions). The LLM prompt changes accordingly.

---

## Contradiction #7: RAG / Knowledge Base Dependency

| | Research Report | Orchestration Plan |
|---|---|---|
| **Recommendation** | RAG with Pinecone/Weaviate + ESAT specification to ground generation and prevent topic drift/factual errors. Listed as a core pipeline component. | No RAG component. Few-shot exemplars from past papers serve a similar grounding function. Factual correctness is handled by SymPy + knowledge in the LLM's pre-training. |
| **Rationale** | LLMs occasionally produce subtly wrong physics/chemistry facts. RAG with verified reference material catches this. The ESAT specification is a natural knowledge base. | The syllabus tree (Phase 0) + classified past paper corpus (Phase 1) + few-shot exemplars already provide strong grounding. Adding a vector DB is unnecessary complexity for v1. SymPy handles the most dangerous error class (math). |

**My recommendation: Go with the Orchestration Plan (no RAG for v1).**

The orchestration plan already has three grounding mechanisms: (1) the syllabus tree constrains topic selection, (2) few-shot exemplars from real past papers constrain style and content, (3) SymPy verifies calculations. Adding a RAG layer would help with chemistry/biology factual accuracy, but those modules are lower priority (lower question volume, harder to verify automatically).

If factual accuracy problems emerge in Chemistry/Biology during the test batch (Phase 4), add a lightweight RAG layer then. But don't build it upfront — it's premature optimisation.

---

## Contradiction #8: Cost per Question Estimate

| | Research Report | Orchestration Plan |
|---|---|---|
| **Estimate** | ~$0.50–1.50 per question end-to-end (including expert review sample) | ~$0.003–0.018 per question for generation (Haiku/Sonnet); ~$49 total for 5,000 questions (~$0.01/question) |
| **Difference** | 50x–150x | |

**My recommendation: The Orchestration Plan's estimate is correct for pure API cost. The Research Report's estimate includes expert review.**

These aren't actually contradictory — they're measuring different things. The orchestration plan estimates API + compute cost only. The research report's range includes human expert review at $2-5/question for a 20% sample, which dominates the cost.

**True cost per question (blended):**
- API generation: ~$0.01–0.02 (orchestration plan estimate)
- Expert review (10% sample at $2-5/Q): ~$0.20–0.50 amortised across all questions
- Infrastructure (negligible): ~$0.001
- **Total: ~$0.21–0.52 per question**

This is still very reasonable for a 5,000-question bank (~$1,000–2,600 total).

---

## Summary Table

| # | Contradiction | Recommended Approach | Source |
|---|---|---|---|
| 1 | Primary LLM model | Tiered Claude routing (Haiku → Sonnet → Opus) with GPT-5 benchmark | Orchestration Plan |
| 2 | Orchestration framework | Custom Python, no LangGraph | Orchestration Plan |
| 3 | Difficulty calibration | Add structural difficulty scoring step (lightweight, pre-deployment) | Research Report (tiered) |
| 4 | Expert review | Add 10% expert review sampling gate | Research Report |
| 5 | Distractor generation | Add computational distractors for calculations + LLM-as-judge filter | Hybrid |
| 6 | Generation order | Solution-first CoT for calculation questions | Research Report |
| 7 | RAG knowledge base | No RAG for v1; add for Chem/Bio if needed | Orchestration Plan |
| 8 | Cost per question | ~$0.21–0.52/question (blended, including expert review) | Reconciliation |

---

## Changes Required to Orchestration Plan

1. **Add Stage 5.5: Structural Difficulty Scoring** — after verification, before storage. Scores each question on 5-6 structural features, compares against target difficulty, flags mismatches.

2. **Add Stage 6.5: Expert Review Sampling** — random 10% sample of accepted questions reviewed by subject expert. Turing test filter. Feedback loop into generation prompts.

3. **Update Template Schema** — add `generation_strategy: "solution_first" | "question_first"` field. For `solution_first` templates, the LLM prompt instructs: "First generate the worked solution, then construct the question."

4. **Add Computational Distractor Module** — for calculation questions with deterministic error transforms (e.g., SUVAT: forget to square, swap sin/cos, use diameter not radius). This runs alongside LLM distractor generation; computational distractors are preferred when available.

5. **Add LLM-as-Judge Distractor Filter** — cheap Haiku pass after generation: evaluate distractor plausibility, length cues, and diagnostic value. Reject and regenerate if filter fails.

6. **Update Cost Model** — revise from ~$49 for 5,000 questions to ~$1,000–2,600 for 5,000 questions (including expert review at 10% sampling).

---

*Prepared by CEO · 28 June 2026*
