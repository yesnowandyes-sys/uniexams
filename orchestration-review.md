# Orchestration Plan Review — Improvements for ESAT Suitability

**Reviewer:** Research Agent  
**Date:** 29 June 2026  
**Document reviewed:** `question_generation_research.md` (2,208 lines, 14 sections)  
**Cross-referenced against:** `esat_format_research.md`, `contradiction-analysis.md`, `DESIGN_PHILOSOPHY.md`, `design.md`

---

## Summary

The orchestration plan is a comprehensive, well-researched document that covers model selection, architecture options, cost analysis, diagram generation, deduplication, and implementation roadmap. It is one of the most thorough question-generation design documents I have reviewed. However, it has **three critical gaps** that will block implementation if not addressed: (1) no concrete calculator-free arithmetic constraint mechanism, (2) missing module-specific syllabus detail for the generation prompts, and (3) absent verification for Chemistry/Biology (SymPy only covers maths/physics). The cost model is realistic for API costs but understates total project cost because it omits the expert review sampling gate agreed in the contradiction analysis. The plan is close to implementation-ready but needs the additions below before a coding agent can build it.

---

## Section-by-Section Findings

### Section 1: Executive Summary

- **Status:** OK
- **Issue:** Recommends Architecture B and states "5,000 questions for approximately $80–$150." Later sections calculate ~$36–$68. The discrepancy is minor but could confuse a coding agent doing budget sanity checks.
- **Recommendation:** Align the executive summary cost range with the detailed calculation in Section 5 ($36–$68 API-only, or ~$200–$600 including 10% expert review per contradiction analysis).

### Section 2: Model Landscape — Pricing & Capabilities

- **Status:** OK
- **Issue:** Pricing tables are thorough and verified. Model names are plausible for mid-2026. No ESAT-specific issues.
- **Minor note:** The plan references "Claude Fable 5" as unavailable — this is fine as a disclaimer but could be removed to reduce confusion for a coding agent.
- **Recommendation:** No changes needed. A coding agent should use Section 2 as a pricing reference table.

### Section 3: Diagram Generation Deep Dive

- **Status:** Needs Improvement
- **Issues:**
  1. **Chemistry diagrams are well-covered** (RDKit + chemfig + pgfplots) — good.
  2. **Biology diagrams acknowledge the "cell diagram problem"** honestly but the solution (pre-drawn SVG template library, ~$200 one-time) is mentioned only in Section 14.5, not in Section 3's recommendations. A coding agent reading Section 3 alone won't know the budget exists.
  3. **No mention of ARM compatibility for RDKit.** RDKit's C++ backend has historically had issues on ARM Linux. The Oracle Cloud VM is ARM (Ampere A1). This needs verification.
  4. **LaTeX on ARM:** TeX Live on ARM Ubuntu is fine, but `pdflatex` compilation can be slow. No mention of compilation caching or parallel compilation.
- **Recommendations:**
  - Add a note in Section 3 that RDKit must be tested on ARM64 before committing to it; fallback is `chemfig` only.
  - Add LaTeX compilation caching guidance (cache compiled TikZ PDFs keyed by TikZ source hash).
  - Move the Biology template budget ($200) from Section 14.5 into Section 3.4 as a first-class budget item.

### Section 4: Multi-Agent Frameworks Comparison

- **Status:** OK
- **Issue:** The plan correctly recommends custom Python over LangGraph (consistent with contradiction analysis #2). However, Section 4.2 says "Custom Python + LangGraph (or just Custom Python)" while later sections assume pure custom Python. This ambiguity could confuse implementation.
- **Recommendation:** Remove the "(or just Custom Python)" hedging. State definitively: **Custom Python, no framework dependency.** This was already agreed in the contradiction analysis.

### Section 5: Proposed Architectures (A–E)

- **Status:** Needs Improvement
- **Issues:**
  1. **Architecture B's per-question token math has a minor error.** Step 1 (Generation) calculates cached input cost at $0.10/MTok (Haiku cache hit rate) but then uses Batch input cost at $0.50/MTok for the new input tokens. These two discounts (cache + batch) do stack, but the cached portion should be charged at $0.10/MTok × 50% batch = $0.05/MTok, not $0.10/MTok. The current math slightly overestimates cost, which is safe but inaccurate.
  2. **Architecture A mentions "No calculator-free reasoning guarantee" as a weakness** but no architecture has this as an explicit pipeline stage. This is a systemic gap (see Section 7 findings).
  3. **Architecture E's 200 questions/week pace** means 5,000 questions takes 25 weeks (~6 months). This may be too slow for the project timeline. The plan should mention an accelerated mode (500/week) and what that does to review burden.
- **Recommendations:**
  - Add a note clarifying that Batch + Cache discounts stack multiplicatively, and recalculate Architecture B's per-question cost with the correct compounded rate.
  - Add a "Calculator-Free Arithmetic Check" as an explicit pipeline stage in the Architecture B/E descriptions (see Top Priority #1).
  - Add an accelerated pace option to Architecture E (500/week at ~4 hours review/week).

### Section 6: Cost Comparison Table

- **Status:** Needs Improvement
- **Issue:** The cost table shows API costs only. The contradiction analysis agreed on a blended cost of ~$0.21–$0.52/question including 10% expert review ($2–$5/Q for reviewed sample). The plan's cost table should reflect this reconciled figure.
- **Recommendation:** Add a "Total Project Cost (incl. expert review)" column to the comparison table showing ~$1,000–$2,600 for Architecture B+E combined. This was explicitly agreed in contradiction analysis #8.

### Section 7: Quality Assurance Strategy

- **Status:** Critical Gap
- **Issues:**
  1. **No calculator-free arithmetic verification.** Layer 3 (Structural Validation) mentions "No calculator required? (check for non-trivial arithmetic)" as a check, but gives no implementation detail. This is the single most important ESAT-specific quality gate and it's a one-line bullet. How does the system detect that √7.3 or 47 × 83 appears in a question? What threshold defines "calculator-required"?
  2. **SymPy coverage is overstated.** The plan says "~70% of Maths/Physics questions" can be verified by SymPy. This is optimistic. SymPy cannot verify: graphical interpretation questions, estimation questions, conceptual physics questions, or questions involving inequalities with physical constraints. Realistic coverage is ~40–50% of Maths/Physics.
  3. **No verification at all for Chemistry and Biology.** The plan acknowledges this implicitly (no SymPy for Chem/Bio) but never proposes an alternative. The contradiction analysis flagged this as the priority area for expert review. A coding agent will notice the gap and have no guidance.
  4. **No "Cambridge voice" authenticity check.** The plan mentions a "style match" rubric in Layer 5 but doesn't describe what ESAT style actually *is* in machine-checkable terms. A coding agent needs concrete style rules.
- **Recommendations:**
  - **Add a dedicated Calculator-Free Arithmetic Checker** as Layer 2.5 of the QA stack (see Top Priority #1 for full spec).
  - Downgrade SymPy coverage claim to "~40–50% of Maths/Physics questions."
  - Add a "Chemistry/Biology Factual Verification" layer: for Chemistry, cross-check stoichiometry and bond energies using RDKit + a reference table; for Biology, use an LLM-as-judge factual check against the ESAT Content Specification document (loaded as context).
  - Add 5–10 concrete ESAT style rules in the QA rubric section (e.g., "Questions use 'Which...' not 'What is the most...' for single-answer MCQs", "Numerical answers are rounded to 2 significant figures", "Distractors are never absurd values — all are physically plausible").

### Section 8: Recommendation

- **Status:** OK
- **Issue:** Recommends combining Architecture B + E, which is sound. The section is clear and actionable.
- **Recommendation:** No changes needed.

### Section 9: Implementation Roadmap

- **Status:** Needs Improvement
- **Issues:**
  1. **Phase 1 timeline is optimistic.** "Download all ENGAA/NSAA past papers → OCR → structured JSON" in Week 1 is aggressive. Many past papers are PDF scans, not born-digital. OCR of mathematical content (subscripts, superscripts, fractions, symbols) is notoriously error-prone. This could easily take 2 weeks alone.
  2. **No mention of the ESAT Content Specification PDF ingestion** in Phase 1, even though Section 10.6 describes it. It should be a Phase 1 deliverable.
  3. **Phase 2 says "Build Python Pipeline"** but lists only a directory structure, not a build sequence. A coding agent needs to know: what to build first, what to test, what constitutes "done" for each component.
  4. **Phase 2 "Test with 100 Questions" is good** but doesn't specify success criteria. What rejection rate is acceptable? What quality threshold?
- **Recommendations:**
  - Extend Phase 1 to 2 weeks and add explicit OCR quality-check step (manually verify 10% of extracted questions against source PDFs).
  - Add ESAT Content Specification PDF ingestion as a Phase 1 task.
  - Add a phased build order for Phase 2: (a) SymPy verifier, (b) structural validator, (c) single-module generator (Maths 1), (d) expand to other modules, (e) diagram pipeline, (f) dedup + coverage.
  - Define Phase 2 success criteria: ≤15% rejection rate, ≥4/5 average rubric score, 100% of Maths/Physics questions pass calculator-free check.

### Section 10: Deep Dive — Pattern Extraction with Opus

- **Status:** OK (strongest section)
- **Issue:** This is the most detailed and useful section. The prompt templates, JSON schemas, and parameterised template examples are excellent and directly implementable.
- **Minor issues:**
  1. **Section 10.3.3's topic weightings are presented as Opus output examples but read like definitive figures.** A coding agent may treat them as ground truth rather than expected Opus output. Label them clearly as "expected output structure, not verified figures."
  2. **Section 10.5's parameterised template example** includes `"calculator_free_constraint": "Values chosen so answer is a clean fraction or simple decimal"` — this field is excellent but it appears in only one template. It should be a mandatory field in ALL templates.
- **Recommendations:**
  - Make `calculator_free_constraint` a required field in the template JSON schema, not optional.
  - Add topic weightings disclaimer: "Actual weightings must be derived from Opus analysis of past papers. The figures below illustrate expected output format."

### Section 11: Deep Dive — Diagram Generation by Subject

- **Status:** Needs Improvement
- **Issues:**
  1. **Strong on Chemistry (RDKit, chemfig, pgfplots), reasonable on Physics (TikZ), weak on Biology** — this is acknowledged honestly.
  2. **No mention of ARM compatibility** for any of the diagram tools. RDKit, in particular, has had ARM build issues historically.
  3. **TikZ compilation on the Oracle Cloud VM:** ARM pdflatex works but may be slow for batch compilation of 50+ diagrams. Consider caching or pre-compiling template variants.
  4. **The Biology "template library" approach is correct** but requires ~$200 and manual creation. No timeline is given for this. It should be a Phase 1 parallel workstream.
- **Recommendations:**
  - Add an ARM compatibility note and fallback plan for RDKit (if RDKit fails on ARM, use chemfig for all Chemistry diagrams).
  - Add a note about TikZ compilation performance on ARM and recommend batch compilation with caching.
  - Add Biology template creation as a Phase 1 parallel task with $200 budget and 1-week timeline.

### Section 12: OpenClaw as Orchestration Layer

- **Status:** OK
- **Issue:** The section is accurate and the hybrid recommendation (OpenClaw cron + Python script) is sound. The cron job example is correct for the current setup.
- **Minor note:** The cron example uses `--module physics` but should probably cycle through modules automatically based on the coverage tracker, not require manual module specification.
- **Recommendation:** Update the cron example to show `--module auto` mode that uses the coverage tracker to select the most underrepresented module.

### Section 13: Infinite Generation — Deduplication & Coverage

- **Status:** OK (good technical detail)
- **Issues:**
  1. **FAISS code example is correct and runnable.** Good.
  2. **Coverage tracker code example is reasonable** but the `COVERAGE_TARGETS` hardcoded dictionary should be populated from Opus pattern extraction output, not hand-coded. The plan says this but the code doesn't show the loading mechanism.
  3. **Threshold of 0.85 is reasonable** for sentence-level dedup. However, the plan doesn't account for questions that test the same concept with completely different wording (semantic duplicates at the concept level). A secondary check based on (module + topic + difficulty + answer_pattern) tuples could catch these.
  4. **No mention of embedding model ARM compatibility.** `sentence-transformers` with `all-MiniLM-L6-v2` should work on ARM CPU (ONNX runtime), but this needs verification.
- **Recommendations:**
  - Add a concept-level dedup check: group questions by (module, topic, difficulty, template_id) and limit to N questions per group.
  - Add a note to test `sentence-transformers` on ARM64 before committing.
  - Make coverage targets loaded from `coverage_targets.json` (Opus output) rather than hardcoded.

### Section 14: Concrete Implementation Architecture

- **Status:** Needs Improvement
- **Issues:**
  1. **Repository structure (Section 14.3) is excellent** — directly implementable. One missing file: `calculator_check.py` in the verifiers directory.
  2. **Dependencies list (Section 14.4) is missing some packages:** `pdfplumber` is mentioned but not in the pip install. `chemfig` is a LaTeX package, not pip. The install commands should be split into Python and LaTeX.
  3. **The end-to-end workflow (Section 14.4) is good** but Step 4d says "Run SymPy verification → if fails, regenerate" without a regeneration limit. A question that can't pass SymPy after 3 attempts should be discarded, not retried infinitely.
  4. **Cost projection (Section 14.5) doesn't include the expert review cost** agreed in contradiction analysis.
  5. **No error handling or retry strategy** for API failures (rate limits, timeouts, malformed responses).
  6. **No database schema.** The plan mentions SQLite/Postgres but doesn't define the question table schema. A coding agent will need this.
- **Recommendations:**
  - Add `verifiers/calculator_check.py` to the repo structure.
  - Fix the dependency installation commands (split Python/LaTeX, add missing packages).
  - Add regeneration limits (max 3 retries per question, then discard).
  - Add a basic database schema for the question bank.
  - Add error handling guidance: exponential backoff on API calls, circuit breaker on repeated failures.
  - Reconcile cost projection with contradiction analysis blended figure.

---

## Top Priority Improvements

### 1. 🔴 CRITICAL: Calculator-Free Arithmetic Checker (Missing)

**What the plan says:** Layer 3 of QA mentions "No calculator required? (check for non-trivial arithmetic)" as a one-liner.

**What's wrong:** ESAT is strictly no-calculator. There is no mechanism to detect questions that require evaluating √3, or multiplying 17 × 23, or computing sin(23°). An LLM will happily generate a physics question where the answer is 7.382 m/s, which is impossible without a calculator.

**Recommended implementation:**
```python
# verifiers/calculator_check.py

import re
from typing import List, Tuple

# Arithmetic that's reasonable mentally for a strong student under time pressure
MENTAL_ARITHMETIC_RULES = {
    "max_multiplication_factors": (12, 20),  # 12×20=240 is borderline mental
    "max_two_digit_mult": False,  # No 17×23 without nice structure
    "allowed_sqrts": [0, 1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144, 169, 196, 225],
    "allowed_trig_angles": [0, 30, 45, 60, 90, 180, 270, 360],
    "max_decimal_places_in_answer": 2,
    "require_exact_or_simple_fraction": True,
}

# Patterns that indicate calculator dependency
CALCULATOR_DEPENDENT_PATTERNS = [
    r'sin\s*\(\s*\d+[°°]\s*\)',  # Non-standard trig angles
    r'cos\s*\(\s*\d+[°°]\s*\)',
    r'tan\s*\(\s*\d+[°°]\s*\)',
    r'√\s*\d+',                    # Square roots of non-perfect squares
    r'sqrt\s*\(\s*\d+\s*\)',
    r'log\s*\(\s*\d+\s*\)',        # Log of non-power-of-10
    r'ln\s*\(\s*\d+\s*\)',
    r'\d+\.\d{3,}',                # Numbers with 3+ decimal places
    r'e\s*\^',                     # Exponential with non-integer exponent
]

def check_calculator_free(question_text: str, options: List[str], 
                           worked_solution: str) -> Tuple[bool, List[str]]:
    """
    Returns (passes, list_of_issues).
    Verifies that the question is solvable without a calculator per ESAT rules.
    """
    issues = []
    full_text = f"{question_text} {' '.join(options)} {worked_solution}"
    
    # Check for calculator-dependent patterns in the question
    for pattern in CALCULATOR_DEPENDENT_PATTERNS:
        matches = re.finditer(pattern, full_text, re.IGNORECASE)
        for match in matches:
            # Check if it's a "nice" value
            if not is_mentally_computable(match.group()):
                issues.append(f"Calculator-dependent value: '{match.group()}'")
    
    # Check numerical answers for cleanliness
    for opt in options:
        if has_ugly_decimal(opt):
            issues.append(f"Answer option '{opt}' has non-mental decimal value")
    
    # Check that intermediate calculations in solution are tractable
    solution_issues = check_solution_arithmetic(worked_solution)
    issues.extend(solution_issues)
    
    return len(issues) == 0, issues

def is_mentally_computable(expression: str) -> bool:
    """Check if a mathematical expression can be reasonably computed mentally."""
    # Extract numbers from the expression
    numbers = re.findall(r'\d+\.?\d*', expression)
    for n in numbers:
        val = float(n)
        # Check against allowed nice values
        if val > 100 and val != int(val):
            return False
        if len(n.split('.')[-1]) > 2 and '.' in n:
            return False
    return True
```

**Also add to the generation prompt system:** A mandatory instruction — *"All numerical values in questions must be chosen so that calculations can be performed mentally within 90 seconds without a calculator. Prefer: integers under 100, fractions with denominators 2/3/4/5/10, standard trig values (0°, 30°, 45°, 60°, 90°), perfect squares up to 225, g = 10 m/s² (not 9.8)."*

### 2. 🔴 CRITICAL: Module-Specific Syllabus Content for Generation Prompts

**What the plan says:** Section 10.3.3 shows example topic weightings as illustration.

**What's wrong:** The plan never produces the actual detailed syllabus breakdown per module that a generation prompt needs. A coding agent building `maths1_gen.py` needs to know: what topics, what sub-topics, what formulas are in scope, what's explicitly out of scope, what difficulty distribution per sub-topic.

**Recommendation:** The Opus pattern extraction (Phase 1) must produce a `syllabus_tree.json` with this structure for each module:
```json
{
  "module": "Maths 1",
  "topics": [
    {
      "topic": "Algebra",
      "weight_pct": 25,
      "subtopics": [
        {
          "name": "Quadratic equations",
          "concepts": ["factorising", "completing the square", "quadratic formula"],
          "formulas_in_scope": ["x = (-b ± √(b²-4ac)) / 2a"],
          "calculator_free_note": "Discriminants should be perfect squares or require simple estimation",
          "typical_difficulty": "medium",
          "sample_parameters": {"a": [-3,3], "b": [-10,10], "c": [-10,10]}
        }
      ]
    }
  ]
}
```

This file must be generated before ANY generation code is written — it's the input to every generator module.

### 3. 🔴 CRITICAL: Chemistry & Biology Verification Strategy

**What the plan says:** SymPy covers ~70% of Maths/Physics. No verification specified for Chemistry or Biology.

**What's wrong:** 30% of questions (Chemistry + Biology) have zero automated verification beyond LLM solver agreement. The contradiction analysis identified this as the priority area for expert review, but the plan doesn't specify even a lightweight automated check.

**Recommendation:** Add two verification approaches:
- **Chemistry:** Stoichiometry checker (parse chemical equations, verify atom balance using RDKit). Bond energy checker (verify ΔH calculations against a reference table). Gas law calculator (verify PV=nT derivations).
- **Biology:** LLM-as-judge factual check — load the ESAT Biology Content Specification as context, have Haiku verify: "Is every factual claim in this question and answer consistent with the specification?" This is cheaper than SymPy and catches the main error class (factual inaccuracies).

### 4. 🟡 HIGH: Structural Difficulty Scoring (from Contradiction Analysis #3)

**What the plan says:** Difficulty is set by the template/directive at generation time. No post-generation difficulty verification.

**What's wrong:** LLMs are unreliable at self-assessing difficulty. A question tagged "medium" might actually be "hard" because of a subtle calculation trap.

**Recommendation:** Implement the structural difficulty scorer agreed in contradiction analysis #3 as `quality/difficulty_scorer.py`:
- Count reasoning steps in worked solution
- Count distinct concepts used
- Measure distractor closeness (edit distance between correct answer and nearest distractor)
- Score 1–10, compare against target difficulty band, flag mismatches

### 5. 🟡 HIGH: Database Schema Definition

**What the plan says:** "SQLite/Postgres — question bank."

**What's wrong:** No schema. A coding agent cannot implement `output/database.py` without knowing the table structure.

**Recommendation:** Add this schema:
```sql
CREATE TABLE questions (
    id TEXT PRIMARY KEY,           -- UUID
    module TEXT NOT NULL,          -- maths1, maths2, physics, chemistry, biology
    topic TEXT NOT NULL,           -- e.g., "kinematics", "circuits"
    subtopic TEXT,
    difficulty TEXT NOT NULL,      -- easy, medium, hard
    difficulty_score REAL,         -- structural score 1-10
    question_text TEXT NOT NULL,   -- Markdown with LaTeX
    options JSON NOT NULL,         -- ["A text", "B text", ...]
    correct_answer TEXT NOT NULL,  -- "A", "B", "C", "D", or "E"
    worked_solution TEXT NOT NULL, -- Markdown with LaTeX
    diagram_svg TEXT,              -- SVG content or NULL
    diagram_type TEXT,             -- tikz, rdkit, matplotlib, template
    source_template TEXT,          -- template_id from patterns.json
    model_used TEXT,               -- which LLM generated this
    quality_score REAL,            -- rubric score 1-5
    calculator_free_pass BOOLEAN,  -- passed calculator check
    sympy_verified BOOLEAN,        -- passed SymPy check
    solver_verified BOOLEAN,       -- passed LLM solver check
    expert_reviewed BOOLEAN DEFAULT FALSE,
    expert_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding_id INTEGER           -- FAISS index reference
);

CREATE TABLE generation_batches (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    module TEXT,
    total_generated INTEGER,
    total_accepted INTEGER,
    total_rejected INTEGER,
    total_cost_usd REAL,
    model_used TEXT
);

CREATE TABLE review_log (
    id TEXT PRIMARY KEY,
    question_id TEXT REFERENCES questions(id),
    reviewer TEXT,
    score REAL,
    notes TEXT,
    reviewed_at TIMESTAMP
);
```

### 6. 🟡 HIGH: Expert Review Sampling Gate (from Contradiction Analysis #4)

**What the plan says:** Section 7 mentions "optional human spot-check 5–10%."

**What's wrong:** The contradiction analysis explicitly agreed to add a 10% expert review sampling gate as a pipeline stage, not an optional extra. The plan hasn't incorporated this.

**Recommendation:** Add "Stage 6.5: Expert Review Sampling" to the pipeline. Sample 10% of accepted questions (stratified by module — oversample Chemistry/Biology). Budget $1,000–$2,500 for 5,000 questions. This was agreed.

### 7. 🟡 HIGH: Solution-First Generation Order (from Contradiction Analysis #6)

**What the plan says:** Standard question-first generation for all question types.

**What's wrong:** The contradiction analysis agreed to use solution-first generation for calculation-heavy questions to guarantee clean numbers and natural distractor generation.

**Recommendation:** Add `generation_strategy: "solution_first" | "question_first"` to the template schema. For calculation templates (Physics mechanics, Maths calculus, Chemistry moles), default to `solution_first`. Update the generation prompt to support both modes.

### 8. 🟡 HIGH: Computational Distractor Generation (from Contradiction Analysis #5)

**What the plan says:** LLM generates distractors from template strategies. SymPy checks they're wrong.

**What's wrong:** No check on distractor plausibility. No computational distractor generation for calculation questions.

**Recommendation:** Implement both additions from contradiction analysis #5:
- Computational distractor transforms for calculation questions (swap sin/cos, use diameter/radius, forget to square)
- LLM-as-judge distractor plausibility filter (Haiku pass: "Are these distractors plausible? Do they correspond to identifiable errors?")

### 9. 🟠 MEDIUM: Error Handling & Retry Strategy

**What the plan says:** Nothing about API failures, rate limits, or malformed responses.

**What's wrong:** A batch of 50 questions will inevitably hit rate limits, timeouts, or LLM formatting errors. Without retry logic, the pipeline will crash.

**Recommendation:** Add:
- Exponential backoff on all API calls (base 1s, max 60s, max 5 retries)
- JSON schema validation of LLM output (reject and retry if output doesn't parse)
- Circuit breaker: if >50% of last 20 questions failed, pause and alert via Telegram
- Max 3 regeneration attempts per question, then discard and log

### 10. 🟠 MEDIUM: ESAT Content Specification PDF Ingestion

**What the plan says:** Section 10.6 describes the approach but it's buried in the pattern extraction deep dive.

**What's wrong:** A coding agent building Phase 1 might miss this critical step. The Content Specification is the authoritative source for what's in/out of scope.

**Recommendation:** Elevate PDF ingestion to a first-class Phase 1 task. The ESAT Content Specification PDF is available at: `https://uat-wp.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/04/30103004/ESAT_Content_Specification_April2025.pdf`. Download and ingest it as step 1 of the pipeline.

### 11. 🟠 MEDIUM: OCR Quality for Past Papers

**What the plan says:** "OCR/extract all questions into structured JSON format."

**What's wrong:** Mathematical OCR is extremely error-prone. Subscripts, superscripts, fractions, Greek letters, and special symbols (∫, √, ≈, ≠) will be mangled by generic OCR. This will produce garbage training data for Opus pattern extraction.

**Recommendation:**
- Use `pix2tex` (LaTeX-OCR) or Mathpix API for mathematical content extraction
- Manually verify 10% of extracted questions against source PDFs
- Flag and fix any questions where extracted answer doesn't match source answer
- Budget 1–2 weeks for this task, not "Week 1"

### 12. 🟢 LOW: Ambiguity in "Custom Python + LangGraph" Wording

- Clean up Section 4.2 to state definitively: Custom Python, no framework.
- Already agreed in contradiction analysis #2.

### 13. 🟢 LOW: Architecture A's Free Tier Rate Limits

- Architecture A relies on GLM free-tier models. Rate limits are mentioned as a weakness but not quantified. For planning purposes, note that z.ai free tier typically allows ~50 requests/minute and daily token caps. This makes Architecture A suitable for ~200 questions/day maximum.

---

## Implementation Readiness Assessment

**Is the plan ready for a coding agent to implement directly?**

**Almost — with the following blockers:**

### Blocking Issues (must resolve before implementation):
1. **No `calculator_check.py` specification** — need the concrete checker logic (provided in this review as Top Priority #1)
2. **No database schema** — the coding agent needs table definitions (provided in this review as Top Priority #5)
3. **No `syllabus_tree.json` structure** — the Opus extraction prompt produces this, but the coding agent needs the schema to write the database loader and coverage tracker
4. **No Chemistry/Biology verification module** — the coding agent needs at least an LLM-as-judge fallback (described in this review as Top Priority #3)

### Near-Blocking (should resolve in first sprint):
5. **No error handling/retry strategy** — add to orchestrator design
6. **No regeneration limits** — add max-retry constants
7. **OCR pipeline not specified** — need tool selection (Mathpix vs pix2tex vs pdfplumber)
8. **Expert review workflow not specified** — need a review interface or at minimum a JSON export format for reviewers

### Non-Blocking (can be refined during implementation):
9. Cost model reconciliation (doesn't block code)
10. ARM compatibility testing (can verify during Phase 1)
11. Biology template budget approval (parallel workstream)
12. LangGraph wording cleanup (editorial)

**Verdict:** With the additions in this review (especially Priorities #1, #3, #5, and #7), the plan is implementation-ready. A coding agent can begin Phase 1 (past paper ingestion + Opus pattern extraction) immediately while the remaining gaps are addressed in parallel.

---

## Appendix: Cross-Reference to Contradiction Analysis

| Contradiction # | Orchestration Plan Status | This Review |
|---|---|---|
| #1 Model selection | ✅ Resolved (tiered Claude) | No change needed |
| #2 Framework | ✅ Resolved (custom Python) | Section 4 wording needs cleanup |
| #3 Difficulty calibration | ❌ Not yet added to plan | Priority #4 — add structural scorer |
| #4 Expert review | ❌ Not yet added to plan | Priority #6 — add sampling gate |
| #5 Distractor generation | ❌ Not yet added to plan | Priority #8 — add computational + judge |
| #6 Generation order | ❌ Not yet added to plan | Priority #7 — add solution-first mode |
| #7 RAG knowledge base | ✅ Resolved (no RAG for v1) | No change needed |
| #8 Cost model | ❌ Not yet reconciled | Priority #6 in Section findings — add blended figure |

---

*Prepared by Research Agent — 29 June 2026*
