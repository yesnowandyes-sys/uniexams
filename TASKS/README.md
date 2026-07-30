# Task Specs

Full specifications for Question Generation issues live here.

The Paperclip issue descriptions may be truncated due to API limits. **Always read the corresponding TASKS file for the full spec before starting work.**

## Current Issues (work in order)

1. **01-clean-slate-and-dedup.md** — Move generated questions to cold storage, deduplicate corpus with source weight merging
2. **02-weighted-coverage.md** — Compute weighted topic/difficulty distribution from enriched corpus, update coverage tracker
3. **03-generation-and-verification.md** — Solution-first generation, 4 exemplars, verification layers 1-5 and 7

Each issue depends on the prior. Do not start issue 2 until issue 1 is complete, etc.

## How to work these

1. Read the full TASKS file for your current issue
2. Read the referenced existing files (generator scripts, quality scripts, coverage tracker, etc.)
3. Implement the changes
4. Test your changes (run scripts, check output)
5. Update the Paperclip issue status to `in_progress` when you start, `done` when complete