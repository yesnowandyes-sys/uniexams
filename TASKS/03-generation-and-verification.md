# Issue: Rebuild generation pipeline — solution-first, exemplars, and full verification stack

**Paperclip ID:** feda36d9-9c12-423f-a329-10ec39b06214
**Order:** 3rd (depends on issues 01 and 02)
**Assignee:** Coding Agent

---

## Part A: Generation pipeline changes

### Solution-first generation (ALWAYS)

The generator must ALWAYS use solution-first approach. Restructure the system prompt so the LLM:
1. First computes the answer using symbolic/mental math (the solution is derived internally before the question exists)
2. Then writes the question text around that committed answer
3. Then generates 3 distractors and a full worked explanation

This guarantees clean calculator-free numbers because the solution is derived first. The current prompt has a weak 'solve internally first' instruction — replace it with a hard structural requirement.

Apply to both `generator_glm.py` and `generator.py`.

### 4 few-shot exemplars per generation call

Before each generation call, query the corpus for real past-paper questions matching the target topic AND difficulty. Include in the prompt:
- Question text
- Options (A/B/C/D)
- Correct answer
- Worked solution (from enrichment JSON `markdown` field)

Query logic:
- Match on `topic_code` and `difficulty_category` from the enrichment data
- Select 4 exemplars (random from matches)
- If fewer than 4 available at that exact topic+difficulty, use however many exist (minimum 1)
- Do NOT fall back to a different difficulty — Gilbert was explicit about this

### Where exemplars come from

The corpus questions table. After the dedup issue runs, the main questions table will have enriched corpus questions with:
- `enrichment.topic_classification.topic_code`
- `enrichment.topic_classification.difficulty_category`
- `enrichment.markdown` (worked solution)
- `question_text`, `options`, `correct_answer`

---

## Part B: Verification stack — Layers 1-5 and 7

All verification layers run AFTER a question is generated. A question must pass ALL layers to be accepted into the database.

### Layer 1: Calculability checker

Rule-based system. Two tiers.

**Tier 1 — REJECT** (hard failures, question is discarded):
- g not equal to 10 (or 9.81 if explicitly given)
- Non-standard angles without context that allows estimation (e.g. sin(37°) without a triangle diagram)
- Answers requiring more than 3 significant figures
- Multiplication of two numbers both above 15 with no nice structure (e.g. 17 × 23, but 16 × 25 is fine)
- Non-terminating decimals beyond 2 decimal places
- Logarithms of non-exact powers (e.g. log(7) is fine, log(1000) is fine, but log(47) without calculator)
- Physical constants not given in the question stem (e.g. using Boltzmann constant without providing it)

**Tier 2 — WARN** (flag for potential review, but accept):
- Non-perfect square roots requiring decimal precision
- Fractions with denominators above 12
- Non-SI units without conversion
- Compound units written with slashes instead of negative indices

Implement as: `scripts/quality/calculability.py`

### Layer 2: SymPy verification

For maths and physics questions containing solvable equations:
1. Extract mathematical expressions from the question and solution
2. Use SymPy to solve symbolically
3. Compare the SymPy result to the stated correct answer
4. If they match, pass. If not, reject.
5. If the question is graphical, conceptual, or has no extractable equation, skip (not applicable).

Covers roughly 40-50% of maths and physics questions.

Implement as: `scripts/quality/sympy_verify.py`
Requires: `pip install sympy`

### Layer 3: Independent LLM solver (UPGRADE existing)

The existing `scripts/quality/solver.py` does a single LLM solve. Upgrade it to:
1. Run 3 independent solve attempts (same model, different temperature or seed)
2. Use majority vote: 3/3 agree = pass, 2/3 agree = pass with warning flag, 1/3 or 0/3 = reject
3. Each attempt gets the question text and options, NOT the explanation
4. The solver must return which option it picks

### Layer 4: Structural difficulty scorer

Deterministic 6-feature system that computes difficulty from the worked solution. Produces a structural score (1-10) alongside the LLM self-assessment score. Both are stored on the question record.

Features:
1. **Reasoning step count** — count distinct steps in the worked solution
2. **Concept integration count** — count distinct topics/concepts referenced
3. **Distractor closeness** — Levenshtein edit distance between correct answer text and nearest distractor text. Closer = harder.
4. **Context familiarity** — standard textbook example (low) vs novel/unusual (high). Heuristic check.
5. **Trap presence** — count identifiable misconception traps in the distractors (e.g. forgetting g/2, mixing sine/cosine, confusing mass/weight)
6. **Option format** — algebraic answers harder than numeric, numeric harder than conceptual

Scoring: weighted combination into a 1-10 scale. Store as `difficulty_score_structural` alongside the existing `difficulty_score` (LLM self-assessment). Both saved so we can compare later.

Implement as: `scripts/quality/structural_difficulty.py`

### Layer 5: FAISS deduplication

Every new generated question must be checked against ALL existing questions (corpus + previously generated).

1. Embed the new question text using sentence-transformers all-MiniLM-L6-v2 (384 dimensions, CPU)
2. Compare against a FAISS IndexFlatIP of all existing question embeddings
3. Cosine similarity > 0.85 = reject as duplicate
4. Also maintain a concept-level cap: no more than 30 questions per (module, topic_code, difficulty_category) group

The FAISS index needs to be built once from the corpus questions and updated incrementally. Store at `data/faiss_index/`.

Install: `pip install faiss-cpu sentence-transformers`
Implement as: `scripts/quality/dedup_check.py`

### Layer 7: Subject-specific factual checking via internet

Use GLM-5.2 with the `web_search` tool enabled to verify domain-specific facts.

For each generated question, send a verification prompt to GLM-5.2 with web_search tool:
- **Chemistry:** valency consistency, charge balance, realistic bond energies, correct molecular geometries
- **Biology:** accurate cell structures, correct genetic ratios, plausible experimental results, correct biochemical pathways
- **Physics:** energy conservation, realistic orders of magnitude, correct formula applications

The verifier should flag specific factual claims it can't confirm. If any claim is flagged as incorrect, reject the question.

This uses the z.ai API — include `tools=[{'type': 'web_search', 'web_search': {}}]` in the API call. Confirmed working with GLM-5.2.

Implement as: `scripts/quality/factual_check.py`

---

## Integration

Update `nightly_run.py` to run all layers in sequence after generation:
1. Layer 1 (calculability) — fast, rule-based
2. Layer 5 (FAISS dedup) — fast, embedding check
3. Layer 2 (SymPy) — medium, ~40-50% applicable
4. Layer 3 (LLM solver 3x) — slow, always runs
5. Layer 4 (structural difficulty) — fast, deterministic
6. Layer 7 (factual check) — slow, web search

A question failing ANY layer is rejected. Log which layer failed and why.

---

## Files

- Modify: `scripts/generator_glm.py`
- Modify: `scripts/generator.py`
- Modify: `scripts/nightly_run.py`
- Upgrade: `scripts/quality/solver.py`
- New: `scripts/quality/calculability.py`
- New: `scripts/quality/sympy_verify.py`
- New: `scripts/quality/structural_difficulty.py`
- New: `scripts/quality/dedup_check.py`
- New: `scripts/quality/factual_check.py`
- New: `data/faiss_index/` (directory for FAISS index)

## Dependencies
- Issue 01 (clean slate + dedup) — needs clean corpus
- Issue 02 (weighted coverage) — needs weightings.json and updated coverage_tracker