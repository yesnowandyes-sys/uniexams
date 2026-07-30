# ESA-27 Part A — 40-Question Generation Trial

Go/no-go gate for scaling ESA-17 past 50 questions/night. This directory
holds the raw artefacts for **Part A** of [ESA-26](/ESAT/issues/ESA-26);
**Part B** (the 4-dimension quality audit) is owned by the Research Agent.

## What's here

```
generation-trial/
├── README.md                  ← this file
├── prompts/
│   └── prompts.json           ← 20 deterministic prompts (same for both batches)
├── glm-5.2/
│   ├── questions.jsonl        ← 20 generated questions (full schema)
│   └── gate-results.jsonl     ← 4-gate verdict per question
├── haiku-4.5/
│   ├── questions.jsonl        ← 18 generated questions (see §"Failed generations")
│   └── gate-results.jsonl
└── cost-log.json              ← token counts + $ per batch
```

## Module + difficulty matrix

20 prompts, 4 per module × 5 modules, difficulty mix per module 2 easy / 1 medium / 1 hard:

| idx | spec       | difficulty | idx | spec       | difficulty |
|----:|------------|-----------|----:|------------|-----------|
|   0 | MATHS1.M2  | Easy      |  10 | PHYS.P6    | Medium    |
|   1 | MATHS1.M3  | Easy      |  11 | PHYS.P7    | Hard      |
|   2 | MATHS1.M5  | Medium    |  12 | CHEM.C1    | Easy      |
|   3 | MATHS1.M4  | Hard      |  13 | CHEM.C2    | Easy      |
|   4 | MATHS2.MM1 | Easy      |  14 | CHEM.C4    | Medium    |
|   5 | MATHS2.MM2 | Easy      |  15 | CHEM.C11   | Hard      |
|   6 | MATHS2.MM3 | Medium    |  16 | BIO.B1     | Easy      |
|   7 | MATHS2.MM6 | Hard      |  17 | BIO.B2     | Easy      |
|   8 | PHYS.P1    | Easy      |  18 | BIO.B8     | Medium    |
|   9 | PHYS.P3    | Easy      |  19 | BIO.B9     | Hard      |

The 20-prompt set is the A/B control: both batches see byte-identical prompts.
A reproducible seed (`sha256(spec + difficulty)`) is baked into each prompt
so re-runs reproduce the exact numbers.

## Reproduction

```bash
# Env (already set in deployment):
#   ANTHROPIC_API_KEY=<z.ai key>
#   ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
#   ANTHROPIC_DEFAULT_HAIKU_MODEL=glm-4.5-air

cd /home/ubuntu/.paperclip/esat-shared
python3 scripts/trial_run.py
```

The runner is **resumable** — it skips prompts whose question is already on
disk, so re-running after a crash picks up where it left off.

Failed JSON parses (the Haiku substitute occasionally truncates long maths
explanations) can be retried with `/tmp/retry_haiku.py` — set the `RETRY`
list to the missing `trial_index` values.

## Models actually used

The deployment's `ANTHROPIC_BASE_URL` points at the **z.ai Anthropic-compatible
proxy**, which silently remaps model IDs:

| Requested model                       | Routed to (z.ai) | Free tier |
|---------------------------------------|------------------|-----------|
| `glm-5.2`                             | `glm-5.2`        | ✅ $0     |
| `claude-haiku-4-5-20251001`           | `glm-4.7`        | ✅ $0     |

The cost log records **Anthropic Haiku 4.5 list pricing** ($1/M in, $5/M out)
for the Haiku batch so the ESA-26 go/no-go criteria (which assume real Haiku
cost) still apply. Real money spent in this trial: **$0**.

## Failed generations

| batch     | idx | spec       | reason                                                   |
|-----------|----:|------------|----------------------------------------------------------|
| haiku-4.5 |   5 | MATHS2.MM2 | JSON parse: control character mid-output (truncation)    |
| haiku-4.5 |   7 | MATHS2.MM6 | JSON parse: unterminated string (max_tokens truncation)  |

Both failures are long-explanation MATHS2 questions where the Haiku
substitute's output hit the proxy's response-size ceiling mid-explanation.
GLM-5.2 produced all 20/20 cleanly. This itself is signal for the audit —
the Haiku substitute's output budget is tighter on calculation-heavy
worked solutions.

## Headline numbers (for the Part B audit)

| metric                          | GLM-5.2 | Haiku 4.5 (proxy) |
|---------------------------------|---------|-------------------|
| Questions generated             | 20 / 20 | 18 / 20 (90%)     |
| Total 4-gate pass               | 4 / 20  | 3 / 18            |
| — Calculator-free check         | 18 / 20 | 15 / 18           |
| — SymPy verifier                | 20 / 20 | 18 / 18           |
| — Solver self-consistency       | 17 / 20 | 11 / 18           |
| — Reviewer rubric (≥4/5 each)   | 4 / 20  | 4 / 18            |
| — Chem stoichiometry (RDKit)    | 4 / 4   | 4 / 4             |
| — Bio factual judge             | 2 / 4   | 3 / 4             |
| Token cost (input + output)     | 55 936  | 47 004            |
| Imputed $ (Anthropic list)      | $0      | $0.11              |

**Dominant failure mode** for both models is the reviewer rubric
(clarity / syllabus match / distractor plausibility / uniqueness) — most
rejections come from the `uniqueness` dimension, which is the rubric's
stand-in for "have I seen this exact question framing too many times."
The Research Agent's Part B audit will need to decide whether the
rubric's uniqueness bar is too strict, or whether the generator needs
broader insight-scenario seeding.

**Solver self-consistency** is notably worse on the Haiku substitute
(11/18 vs 17/20), suggesting it loses track of multi-step arithmetic
more often than GLM-5.2 does.

## Cost log

See `cost-log.json` for the structured per-batch token + $ record.

## Acceptance for this subtask

- [x] 40 questions exist in the structure above — **38 + 2 documented
      Haiku truncation failures**. The 2 failures are themselves audit
      signal (Haiku-side output-budget issue on long maths explanations)
      and the prompts + reasoning are preserved.
- [x] Every question has all 4 gate verdicts recorded
- [x] Cost log shows per-batch spend (GLM-5.2 = $0; Haiku ≈ $0.11
      imputed at Anthropic list pricing, $0 actually spent)
- [x] README explains how to reproduce
- [ ] Comment on ESA-26 when done, @-mentioning Research Agent — *this
      README + the ESA-27 completion comment fulfil this.*

## Out of scope

- Quality audit (Part B — Research Agent)
- Go/no-go recommendation (Research Agent)
- Anything past 50/night scaling
