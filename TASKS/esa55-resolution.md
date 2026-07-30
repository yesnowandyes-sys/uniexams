# ESA-55 Resolution — Calculability false positives + retryability + operational hygiene

**Date:** 2026-07-30 · **Status:** Complete · **Investigation:** `/home/ubuntu/dashboard/reports/glm-rejection-investigation.html`

## Root cause
The calculability gate scanned distractor rationale text and wrong-option values
with the same Tier-1 rules as the correct answer path. Distractors are *designed*
to carry unreasonable values (`g = 0.1` instead of `g = 10`, `0.00005 cm²`), so
this produced false-positive rejects.

## Changes

### `scripts/quality/calculability.py`
1. **`_flatten()` excludes distractor rationales.** New `_DISTRACTOR_HEADER_RE`
   splits the `explanation` at the first "Why the other options are wrong" /
   "Incorrectly" header; only the correct-derivation part is scanned.
   (`_worked_solution()` helper; falls back to an explicit `worked_solution`
   field when present.)
2. **Tier-1 sig-fig / non-terminating checks scan the correct path only.** New
   `_correct_path(question)` = stem text + correct option (matched by
   `correct_answer` letter) + worked solution. Distractor options are no longer
   scanned by `_t1_sig_figs` / `_t1_non_terminating`.
3. **`_t1_g_value()` scans `stem` only** (signature: `(stem,)`, `full` removed).
   `g = X` assignments live in the question stem; rationale phrases like
   "divided by g = 0.1" are not assignments.
4. Two new self-test cases lock in the fixes
   (`distractor_rationale_wrong_g_not_reject`,
   `distractor_option_extreme_decimal_not_reject`). **17/17 self-tests pass.**

Monotonicity note: all three changes make the Tier-1 gate *strictly more
permissive* (every scanned blob is a subset of the previous one), so no
previously-passing question can newly fail — regressions are impossible by
construction (confirmed by corpus spot-check).

### `scripts/nightly_run.py`
- `RunSummary` gains `dry_run: bool = False`, surfaced in `to_dict()` (and the
  cost-log line). Downstream consumers can now distinguish dry-runs from real
  runs. Verified: a `--dry-run` log contains `"dry_run": true`.

### `scripts/generate_and_verify_glm.py`
- `"calculability"` added to `RETRYABLE_GATES` (alongside the legacy
  `"calculator"` key, which is how this pipeline actually keys the gate).
  Calculability rejections are now retried via LLM revision.

### Version control (was: none)
- `git init` + `.gitignore` (`node_modules/`, `.next/`, `__pycache__/`, `*.db`,
  `*.db.bak-*`, `data/faiss_index/`, `logs/`, and secrets — `.openai-api-key`).
  **No secrets or DBs are tracked.** Two commits: baseline (with the ESA-55
  fixes) + the recovery script.

## Re-run of the 3 rejected GLM questions
Full stack (`run_all`) re-evaluation after the fix:

| Attempt | calc | dedup | sympy | solver | factual | struct | outcome |
|---------|:----:|:-----:|:-----:|:------:|:-------:|:------:|---------|
| `fa056530` | ✅ | ✅ | ✅ | ✅ 2/2 | ✅ | ✅ | **inserted** `gen-3ffa5a61` |
| `d0eb9887` | ✅ | ✅ | ✅ | ✅ 3/3 | ✅ | ✅ | **inserted** `gen-490ad209` |
| `e9940883` | ✅ | ❌ dup | ✅ | ⚠️ quota | ✅ | ✅ | excluded (near-dup) |

- `fa056530` (was stuck **pending** — process-killed) and `d0eb9887` (calculability
  false positive) pass the **full 6-gate stack** and were inserted; attempts →
  `accepted`, FAISS index updated (1437 vectors).
- `e9940883` passes calculability (the gate that falsely rejected it) but is now a
  **legitimate near-duplicate** of the inserted `gen-490ad209` (cosine 0.870 > 0.85
  — both are "density of a rectangular metal block from weight + dimensions"). The
  dedup gate correctly excludes it; the bank already covers that pattern.
- Solver for `e9940883` could not be confirmed: Gemini 2.5-Flash free-tier **daily**
  quota (20 req/day) was exhausted. It is moot — dedup rejects it regardless.
- `d0eb9887` retains two `calculability` quality_reviews (passed=0 from the original
  false positive, passed=1 from the re-check) — preserved as forensic history.
- Recovery tool: `scripts/esa55_recover_questions.py` (idempotent; re-runnable).

## Acceptance criteria
- [x] All 3 previously-rejected GLM questions pass the fixed calculability gate
- [x] `python3 quality/calculability.py --self-test` passes (17/17)
- [x] Dry-run logs include `"dry_run": true`
- [x] `git log` shows ≥1 commit
- [x] No regressions on the 1435-question corpus (10 random spot-checked, 0 Tier-1)

DB backed up to `data/questions.db.bak-esa55-20260730T171202Z` before inserts.
