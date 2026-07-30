# TASK: Fix Generator — Add difficulty_score, subject, diagram support, enforce coverage

**Priority:** High
**Assignee:** Coding Agent
**Files:** scripts/generator_glm.py, scripts/generator.py, scripts/nightly_run.py

## Problem

Four gaps in the current question generator compared to the Question Generation Guide plan.

### 1. No numeric difficulty_score
Prompt asks for `difficulty_band` (Easy/Medium/Hard/Very Hard) but NOT a numeric `difficulty_score` (1-5). DB column exists but is always NULL.

### 2. No subject field
`subject` column always blank for generated questions. Generator knows spec code and module but never stores the specific topic name.

### 3. Coverage-based generation not enforced
`coverage_tracker.py` and `nightly_run.py` implement balanced generation, but the 171 existing generated questions were produced via `generator_glm.py --batch` (random shuffle) — NOT through `nightly_run.py`. Topic distribution is random, not balanced.

### 4. No diagram support
Question Generation Guide Section 4 specifies parameterised TikZ diagram templates. ~24-31% of ESAT questions need diagrams. Completely unimplemented.

## Changes Required

### Prompt changes (SYSTEM_PROMPT in both generator_glm.py and generator.py)

Add these fields to the output JSON schema, after `difficulty_band`:
```json
"difficulty_score": <1-5 integer>,
"subject": "<specific topic name from the ESAT taxonomy, e.g. Quantum Physics, Organic Chemistry, Kinematics>",
"has_diagram": <true|false>,
"diagram_description": "<if has_diagram is true, describe the diagram needed in detail. If no diagram, empty string>"
```

Add instructions:
- "If the question conceptually requires a diagram to be solvable (e.g. circuit, force diagram, graph, experimental setup), set has_diagram to true and describe it in detail. If the question is fully text-solvable, set has_diagram to false."
- "difficulty_score is a numeric 1-5 self-assessment where 1 is straightforward recall and 5 is a multi-step problem requiring synthesis of multiple concepts."
- "subject must match a topic name from the ESAT Content Specification taxonomy provided in the pattern brief."

### Validation changes (validate_question in generator_glm.py)

- difficulty_score must be an integer 1-5
- subject must be a non-empty string
- has_diagram must be a boolean
- diagram_description must be a string (can be empty when has_diagram is false)

### DB insert changes (nightly_run.py _insert_accepted)

- Populate `subject` column from question["subject"]
- Ensure difficulty_score is populated from question["difficulty_score"]
- Store has_diagram and diagram_description in metadata JSON

### Coverage enforcement (generator_glm.py batch mode)

In run_batch(), replace random shuffle with coverage_tracker logic. Import coverage_tracker and call pick_next() in the loop. Fall back to old shuffle only if coverage tracker has no targets.

## Diagram approach

Two phases:
- **Phase A (this issue):** Add `has_diagram` + `diagram_description` fields. Store in metadata. Generate diagram-needing questions now, render later.
- **Phase B (separate issue later):** Build TikZ template library per Question Generation Guide Section 4.

## Reference
- Question Generation Guide: /home/ubuntu/dashboard/reports/question-generation-guide.html (Section 4 for TikZ diagram plan)
- Taxonomy: /home/ubuntu/.paperclip/esat-shared/esat_taxonomy.json
- Coverage tracker: scripts/coverage_tracker.py
- Nightly run: scripts/nightly_run.py
- Generator (GLM): scripts/generator_glm.py
- Generator (Gemini): scripts/generator.py
