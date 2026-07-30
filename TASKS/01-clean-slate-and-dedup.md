# Issue: Clean slate + Cross-source deduplication

**Paperclip IDs:** 70c867c6-bf1e-410c-9798-2942e8eef86f (primary), 61df9701-6a90-401e-a9e3-37b6f46e7f9b (stale duplicate — ignore)
**Order:** 1st (blocks everything else)
**Assignee:** Coding Agent

## Part A: Move generated questions to cold storage

Move all 293 questions where `source = 'generated'` from the main `questions` table into a new table `questions_generated_v1`.

- Create `questions_generated_v1` with the same schema as `questions`
- INSERT all generated questions into it
- DELETE them from `questions`
- They stay queryable but will NOT be served by the website or used as exemplars
- The main `questions` table should then contain only the enriched corpus questions

## Part B: Cross-source deduplication with source weight merging

The corpus contains questions from multiple exams. Some questions appear in both ENGAA and NSAA. These should be merged into a single record.

### Source weights (derive from question ID prefix)

| Prefix | Source | Weight |
|--------|--------|--------|
| ESAT-* | ESAT Specimen | 1.0 |
| NSAA-*-S1-* | NSAA Section 1 | 0.95 |
| ENGAA-*-S1-* | ENGAA Section 1 | 0.85 |
| TMUA-*-P1-* | TMUA Paper 1 | 0.75 |
| NSAA-*-S2-* | NSAA Section 2 | 0.75 if physics/chemistry, 0.50 if biology |

Biology NSAA S2 gets 0.50 because it has the most filtering. Derive subject from the enrichment's `topic_classification.module` field.

### Dedup process

1. Normalise question text (strip LaTeX, lowercase, collapse whitespace)
2. Compute cosine similarity between all pairs using sentence-transformers (all-MiniLM-L6-v2, 384-dim, CPU is fine)
3. Pairs with cosine > 0.92 are duplicates
4. For each duplicate group: keep one record as primary, add all other source papers to a `sources` JSON array column, sum the source weights into `source_weight`
5. Add `source_weight` column to `questions` table (float, default 1.0 for single-source questions)
6. Add `sources` column to `questions` table (JSON array of source paper identifiers)

### Important rules

- Preserve enrichment JSON on the primary record. If both records have enrichment, keep the one from the higher-weight source. If only one has enrichment, keep that one as primary.
- 69 questions are flagged `is_out_of_spec: true` in their enrichment. Exclude these from dedup merging but do NOT delete them.
- This should be a standalone script: `scripts/dedup_corpus.py`

### Files

- Database: `/home/ubuntu/.paperclip/esat-shared/data/questions.db`
- New script: `scripts/dedup_corpus.py`
- Install: `pip install sentence-transformers`