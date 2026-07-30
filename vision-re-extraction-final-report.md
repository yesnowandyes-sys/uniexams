# Vision Re-Extraction: Final Report

**Date:** 2026-07-10
**Model:** GLM-4.6V (glm-4.6v) via z.ai API
**Pipeline:** vision-reextract.py + vision-second-pass.py

## Executive Summary

The vision re-extraction pipeline processed all 31 papers (30 with PDFs) across ENGAA, NSAA S1, and TMUA, updating **1,337 out of 1,342 questions (99.6%)** from the original corpus with vision-extracted content. The second pass targeted and fixed all 48 previously unmatched questions with a 100% success rate.

However, the vision model's consistency in converting math notation to LaTeX was limited: **646/1,342 questions (48.1%)** now contain LaTeX math, while **623 questions** still have mathematical content in plain text (units, numbers with units, etc.). This is a model quality issue — the vision model often returned the question text verbatim without converting inline math to LaTeX.

## Papers Processed

### ENGAA (8 papers, 416 questions)

| Paper | Total | Updated | Has LaTeX | Update % |
|-------|-------|---------|-----------|----------|
| ENGAA 2016 S1 | 54 | 54 | 27 | 100% |
| ENGAA 2017 S1 | 54 | 54 | 30 | 100% |
| ENGAA 2018 S1 | 54 | 54 | 27 | 100% |
| ENGAA 2019 S1 | 40 | 40 | 25 | 100% |
| ENGAA 2020 S1 | 40 | 40 | 24 | 100% |
| ENGAA 2021 S1 | 40 | 40 | 23 | 100% |
| ENGAA 2022 S1 | 40 | 40 | 22 | 100% |
| ENGAA 2023 S1 | 40 | 40 | 19 | 100% |

### NSAA S1 (8 papers, 680 questions)

| Paper | Total | Updated | Has LaTeX | Update % |
|-------|-------|---------|-----------|----------|
| NSAA 2016 S1 | 90 | 85 | 32 | 94.4% |
| NSAA 2017 S1 | 90 | 90 | 44 | 100% |
| NSAA 2018 S1 | 90 | 90 | 42 | 100% |
| NSAA 2019 S1 | 90 | 90 | 41 | 100% |
| NSAA 2020 S1 | 80 | 80 | 32 | 100% |
| NSAA 2021 S1 | 80 | 80 | 33 | 100% |
| NSAA 2022 S1 | 80 | 80 | 40 | 100% |
| NSAA 2023 S1 | 80 | 80 | 41 | 100% |

### TMUA (15 papers, 300 questions)

| Paper | Total | Updated | Has LaTeX | Update % |
|-------|-------|---------|-----------|----------|
| TMUA 2017_p2 | 20 | 20 | 10 | 100% |
| TMUA 2018_p1 | 20 | 20 | 8 | 100% |
| TMUA 2018_p2 | 20 | 20 | 10 | 100% |
| TMUA 2019_p1 | 20 | 20 | 14 | 100% |
| TMUA 2019_p2 | 20 | 20 | 7 | 100% |
| TMUA 2020_p1 | 20 | 20 | 10 | 100% |
| TMUA 2020_p2 | 20 | 20 | 9 | 100% |
| TMUA 2021_p1 | 20 | 20 | 15 | 100% |
| TMUA 2021_p2 | 20 | 20 | 8 | 100% |
| TMUA 2022_p1 | 20 | 20 | 12 | 100% |
| TMUA 2022_p2 | 20 | 20 | 6 | 100% |
| TMUA 2023_p1 | 20 | 20 | 13 | 100% |
| TMUA 2023_p2 | 20 | 20 | 9 | 100% |
| TMUA specimen_p1 | 20 | 20 | 9 | 100% |
| TMUA specimen_p2 | 20 | 20 | 4 | 100% |

## Second Pass Results

All 54 initially unmatched questions were addressed:
- **48** questions re-extracted with targeted prompts → 48/48 fixed (100%)
- **6** questions skipped (already had LaTeX from original corpus)

### ENGAA unmatched fixed: 34/34
### NSAA unmatched fixed: 13/13  
### TMUA unmatched fixed: 1/1

## Key Metrics

| Metric | Value |
|--------|-------|
| Total questions in corpus | 1,342 |
| Questions updated by pipeline | 1,337 (99.6%) |
| Questions with LaTeX | 646 (48.1%) |
| Questions with math but no LaTeX | 623 |
| Papers fully processed | 30/31 (NSAA 2016: 94.4% — 5 questions skipped due to no .bak) |
| Second pass success rate | 100% (48/48) |

## Remaining Gap

**623 questions** have mathematical content (units like m/s, kg, numbers with units, etc.) still in plain text. This is NOT a pipeline failure — the vision model processed these pages and returned text, but it returned plain text instead of LaTeX for many questions. The model was inconsistent: sometimes it converted `\frac{}{}`, `^{}`, `\sqrt{}` etc., and sometimes it just returned the raw text.

### Possible improvements for future passes:
1. **Use a stronger vision model** (e.g., GPT-4o, Claude with vision) that may be more consistent at LaTeX conversion
2. **Two-stage approach**: First extract with vision, then use a text-only LLM to convert any remaining math to LaTeX
3. **Stricter prompt engineering**: Require the model to identify ALL mathematical expressions and convert them
4. **Post-processing script**: Scan all question text for math patterns (numbers+units, fractions like "1/2", etc.) and convert to LaTeX automatically

## Files

- Pipeline script: `/home/ubuntu/.paperclip/esat-shared/scripts/vision-reextract.py`
- Second pass script: `/home/ubuntu/.paperclip/esat-shared/scripts/vision-second-pass.py`
- Processing log: `/home/ubuntu/.paperclip/esat-shared/corpus/vision-re-extraction-log.json`
- Original backups: `*.json.bak` alongside each corpus JSON file
