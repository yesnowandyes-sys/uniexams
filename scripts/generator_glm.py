#!/usr/bin/env python3
"""
ESAT question generator using GLM-5.2 via z.ai — ESA-39.

Same prompt engineering, pattern loading, and output parsing as the Gemini
generator (generator.py). The ONLY difference is the LLM backend: this
script uses the OpenAI SDK pointing at z.ai's GLM-5.2 model.

Usage:
    # Single question
    python3 generator_glm.py --spec-code PHYS.P1 --difficulty Easy

    # Batch mode — cycle through all specs × difficulties
    python3 generator_glm.py --batch

    # Dry run — show prompt without calling API
    python3 generator_glm.py --spec-code CHEM.C4 --difficulty Hard --dry-run

Environment:
    ZAI_API_KEY  — Required. z.ai API key.

Reference: generator.py (Gemini version), glm-enrichment.py (z.ai API patterns)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import re
import signal
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import openai

# ESA-45 Part A: few-shot corpus exemplars (sibling module in scripts/).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exemplars  # noqa: E402

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPTS_DIR.parent
PATTERNS_DIR = SHARED_DIR / "patterns"
OUTPUT_DIR = SHARED_DIR / "data" / "generated_glm"

ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
DEFAULT_MODEL = "glm-5.2"

MAX_RETRIES = 5
RETRY_BASE_DELAY = 2.0  # seconds, doubled per retry
MAX_TOKENS = 32768

VALID_DIFFICULTIES = ("Easy", "Medium", "Hard")

# Module code → DB module string (same mapping as generator.py)
SPEC_PREFIX_TO_MODULE: dict[str, str] = {
    "MATHS1": "maths1",
    "MATHS2": "maths2",
    "PHYS": "physics",
    "CHEM": "chemistry",
    "BIO": "biology",
}

# Quota guard endpoint
QUOTA_URL = "http://127.0.0.1:8081/api/zai-quota"

# Per-question quota guard tuning (see ESA-40).
# Roughly 3500 tokens per question ≈ 0.05% of the weekly cap; with a 2x
# safety buffer we stop once headroom drops below 0.1%.
QUOTA_COST_PER_QUESTION_PCT = 0.05
QUOTA_SAFETY_BUFFER = 2.0
QUOTA_HEADROOM_THRESHOLD_PCT = QUOTA_COST_PER_QUESTION_PCT * QUOTA_SAFETY_BUFFER  # 0.1

# Graceful shutdown flag
_shutdown = False


def _handle_sigint(signum: int, frame: Any) -> None:
    global _shutdown
    _shutdown = True
    logger.info("SIGINT received — finishing current question, then exiting...")


signal.signal(signal.SIGINT, _handle_sigint)


# ──────────────────────────────────────────────────────────────────────────
# API key resolution
# ──────────────────────────────────────────────────────────────────────────


def _zai_catalog_key() -> Optional[str]:
    """Try to read the API key from the z.ai plugin catalog.

    Mirrors the fallback in fix-unverified.py / glm-enrichment.py so the
    generator works in environments where ZAI_API_KEY is not exported but
    the OpenClaw z.ai plugin has been installed.
    """
    for candidate in [
        Path(__file__).resolve().parent.parent.parent.parent
        / ".openclaw" / "agents" / "esat-manager" / "agent" / "plugins" / "zai" / "catalog.json",
        Path.home() / ".openclaw" / "agents" / "esat-manager" / "agent" / "plugins" / "zai" / "catalog.json",
    ]:
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text())
                key = data.get("providers", {}).get("zai", {}).get("apiKey")
                if key:
                    return key
            except Exception:
                pass
    return None


def resolve_api_key(cli_key: Optional[str]) -> Optional[str]:
    """Resolve the z.ai API key from CLI arg, env, or OpenClaw catalog."""
    return cli_key or os.environ.get("ZAI_API_KEY") or _zai_catalog_key()


# ──────────────────────────────────────────────────────────────────────────
# Pattern loading (copied verbatim from generator.py)
# ──────────────────────────────────────────────────────────────────────────


def spec_to_module(spec_code: str) -> str:
    prefix = spec_code.split(".", 1)[0].upper()
    if prefix not in SPEC_PREFIX_TO_MODULE:
        raise ValueError(
            f"Unknown spec prefix {prefix!r} (from {spec_code!r}). "
            f"Known: {sorted(SPEC_PREFIX_TO_MODULE)}"
        )
    return SPEC_PREFIX_TO_MODULE[prefix]


@dataclass
class PatternBundle:
    spec_code: str
    style_guide: str
    distractor_catalogue: dict[str, Any]
    insight_scenarios: dict[str, Any]
    base_dir: Path

    @property
    def template_id(self) -> str:
        try:
            return f"{self.spec_code}:{int(self.base_dir.stat().st_mtime)}"
        except OSError:
            return self.spec_code


def load_pattern_bundle(spec_code: str, patterns_dir: Path = PATTERNS_DIR) -> PatternBundle:
    d = patterns_dir / spec_code
    if not d.is_dir():
        raise FileNotFoundError(f"No pattern directory at {d}")

    style_path = d / f"style_guide.{spec_code}.md"
    distractor_path = d / f"distractor_catalogue.{spec_code}.json"
    insight_path = d / f"insight_scenarios.{spec_code}.json"

    missing = [p for p in (style_path, distractor_path, insight_path) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"Pattern bundle for {spec_code} incomplete; missing: {missing}"
        )

    return PatternBundle(
        spec_code=spec_code,
        style_guide=style_path.read_text(encoding="utf-8"),
        distractor_catalogue=json.loads(distractor_path.read_text(encoding="utf-8")),
        insight_scenarios=json.loads(insight_path.read_text(encoding="utf-8")),
        base_dir=d,
    )


# ──────────────────────────────────────────────────────────────────────────
# System prompt + user prompt rendering (copied verbatim from generator.py)
# ──────────────────────────────────────────────────────────────────────────


SYSTEM_PROMPT = """\
You are an expert ESAT (Engineering and Science Admissions Test) question \
author. You write original, exam-calibre multiple-choice questions from a \
per-topic pattern brief.

## GENERATION PROCESS — SOLUTION-FIRST (MANDATORY; DO NOT DEVIATE)

This pipeline is **SOLUTION-FIRST**. You MUST derive the answer BEFORE the \
question exists, then build the question around that committed answer. \
Deriving the answer first is what guarantees every number is calculator-free. \
Produce the JSON object with fields written in EXACTLY this order — the order \
is enforced and is what prevents mid-output self-correction drift. You may \
not reorder fields or revise an earlier field after it is written.

**PHASE 0 — SOLVE & COMMIT (write `_solution_commit` FIRST, before any \
question text).** Before writing any of the question, work the problem to a \
complete, final answer using symbolic / mental arithmetic only. Then OPEN the \
JSON with the `_solution_commit` field. It must contain the full worked \
derivation (equations + arithmetic) and end with a final line in EXACTLY this \
form on its own line: `COMMITTED ANSWER: <letter>` where `<letter>` is one of \
A,B,C,D,E. This field is the single source of truth for the answer; once \
written the committed letter is FROZEN and may not change.

**PHASE 1 — BUILD THE QUESTION AROUND THE COMMITTED ANSWER (write \
`question_text`, `options`, `correct_answer`).** Write the question text, \
then all FIVE options (placing the committed answer at its letter), then \
`correct_answer` (which MUST equal the Phase-0 committed letter). Do NOT \
revise any number or the answer to make the question "nicer" — the numbers \
already came from your Phase-0 solution.

**PHASE 2 — WORKED SOLUTION (write `explanation`).** Re-derive the committed \
answer as a clean textbook worked solution, ending with an explicit statement \
that the derivation lands on option `correct_answer`. Forbidden: any "Wait…", \
"Let me reconsider…", "Actually…", "I'll adjust…" self-correction phrasing. \
If you notice an inconsistency you MUST have caught it in PHASE 0; in the \
output you present only the final, settled derivation.

**PHASE 3 — DISTRACTOR ANALYSIS (write `distractor_analysis`).** For EACH \
wrong option (the four letters that are not `correct_answer`), write one \
short line explaining the misconception or arithmetic slip that would lead a \
candidate to pick it. Format:

```
"distractor_analysis": {
  "<wrong_letter_1>": "<one-line misconception>",
  "<wrong_letter_2>": "<one-line misconception>",
  "<wrong_letter_3>": "<one-line misconception>",
  "<wrong_letter_4>": "<one-line misconception>"
}
```

Do NOT include `correct_answer` as a key in `distractor_analysis`. Do NOT \
revise `correct_answer`, `options`, `explanation`, or `_solution_commit` \
while writing this step.

## OUTPUT FORMAT (EXACT FIELD ORDER — `_solution_commit` ALWAYS FIRST)

```json
{
  "_solution_commit": "<full Phase-0 derivation ending with the line: COMMITTED ANSWER: <letter>>",
  "question_text": "...",
  "options": {"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."},
  "correct_answer": "<one of A,B,C,D,E — must equal the committed letter>",
  "explanation": "<clean worked solution ending on the committed answer>",
  "distractor_analysis": {
    "<each wrong letter>": "<one-line misconception>"
  },
  "difficulty_band": "<Easy|Medium|Hard|Very Hard>",
  "difficulty_score": <1-5 integer>,
  "subject": "<specific topic name from the ESAT taxonomy, e.g. Quantum Physics, Organic Chemistry, Kinematics>",
  "has_diagram": <true|false>,
  "diagram_description": "<if has_diagram is true, describe the diagram needed in detail — what it shows, labels, axes, key dimensions. If no diagram, empty string>"
}
```

Output ONLY the JSON object. No prose before or after. No ``` fences.

## FIELD INSTRUCTIONS

- **difficulty_score** is a numeric 1-5 self-assessment where 1 is straightforward recall and 5 is a multi-step problem requiring synthesis of multiple concepts.
- **subject** must match a topic name from the ESAT Content Specification taxonomy provided in the pattern brief.
- If the question conceptually requires a diagram to be solvable (e.g. circuit, force diagram, graph, experimental setup), set **has_diagram** to true and describe it in detail in **diagram_description** — what it shows, labels, axes, key dimensions. If the question is fully text-solvable, set has_diagram to false and diagram_description to an empty string.

## NON-NEGOTIABLE EXAM CONVENTIONS

- Gravitational field strength: g = 10 N kg⁻¹ (ALWAYS).
- Angles: {0, 30, 45, 60, 90} degrees only.
- Arithmetic: Doable without a calculator. Integer-friendly.
- Options: Exactly FIVE (A, B, C, D, E).
- Correctness: Exactly ONE option must be correct.
"""


def render_user_prompt(
    bundle: PatternBundle,
    difficulty: str,
    *,
    seed: Optional[int] = None,
    exemplars_block: str = "",
) -> str:
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {VALID_DIFFICULTIES}; got {difficulty!r}")

    distractors = bundle.distractor_catalogue.get("distractors", [])[:3]
    scenarios = bundle.insight_scenarios.get("scenarios", [])[:2]

    distractor_block = "\n".join(
        f"- **{d.get('distractor_type', '?')}**: {d.get('generation_strategy', d.get('why_effective', ''))}"
        for d in distractors
    ) or "- (No distractor patterns documented — design plausible misconceptions.)"

    scenario_block = "\n".join(
        f"- {s.get('scenario_description', '')} (insight: {s.get('key_insight', '')}; band {s.get('difficulty_band', '?')})"
        for s in scenarios
    ) or "- (No insight scenarios documented — design an original scenario.)"

    seed_line = f"\n\nRANDOM_SEED: {seed} (use this to pick concrete numbers deterministically)" if seed is not None else ""

    # ESA-45 Part A: few-shot exemplar block, fetched by the caller (generate()).
    exemplar_section = f"\n\n{exemplars_block}" if exemplars_block else ""

    return f"""## SPEC CODE
{bundle.spec_code}

## TARGET DIFFICULTY
{difficulty}

## STYLE GUIDE (Opus-extracted from corpus)
{bundle.style_guide}

## DISTRACTOR PATTERNS (use at least 2)
{distractor_block}

## INSIGHT SCENARIOS (use 1 as the conceptual spine)
{scenario_block}
{seed_line}{exemplar_section}

## TASK
Write ONE original ESAT question for spec code {bundle.spec_code} at {difficulty} difficulty.

Follow the SOLUTION-FIRST protocol in the system prompt, in strict order:
0. Solve and commit — write `_solution_commit` FIRST (derivation + `COMMITTED ANSWER: <letter>`).
1. Build the question around the committed answer — `question_text`, `options`, `correct_answer`.
2. Write `explanation` re-deriving the committed answer (no self-correction).
3. Write `distractor_analysis` for each of the four wrong options.

Output only the JSON object, fields in the order shown in the system prompt.
"""


# ──────────────────────────────────────────────────────────────────────────
# Output parsing + validation (copied verbatim from generator.py)
# ──────────────────────────────────────────────────────────────────────────


_OPTIONS_RE = re.compile(r"^[A-E]$")


def parse_question(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM output is not valid JSON: {exc}\n--- raw ---\n{text[:500]}") from exc

    validate_question(obj)
    return obj


def validate_question(obj: dict[str, Any]) -> None:
    issues: list[str] = []
    if not isinstance(obj, dict):
        raise ValueError("Question is not a JSON object")

    # ESA-45: solution-first — the `_solution_commit` field must be present
    # and non-empty. It is the proof the answer was derived before the
    # question was written.
    commit = obj.get("_solution_commit")
    if not isinstance(commit, str) or not commit.strip():
        issues.append(
            "`_solution_commit` missing/empty — solution-first Phase 0 was "
            "not performed (write the derivation + COMMITTED ANSWER first)"
        )

    required_strings = ("question_text", "correct_answer", "explanation")
    for k in required_strings:
        v = obj.get(k)
        if not isinstance(v, str) or not v.strip():
            issues.append(f"missing/empty `{k}`")

    options = obj.get("options")
    if not isinstance(options, dict):
        issues.append("`options` must be an object")
    else:
        keys = sorted(options.keys())
        if keys != ["A", "B", "C", "D", "E"]:
            issues.append(f"`options` keys must be A–E; got {keys}")
        for k, v in options.items():
            if not isinstance(v, str) or not v.strip():
                issues.append(f"`options.{k}` empty")

    ca = obj.get("correct_answer")
    if isinstance(ca, str) and not _OPTIONS_RE.match(ca):
        issues.append(f"`correct_answer` must be A–E; got {ca!r}")

    da = obj.get("distractor_analysis")
    if not isinstance(da, dict):
        issues.append(
            "`distractor_analysis` must be an object keyed by the four wrong "
            "option letters (STEP 4 of the strict CoT flow)"
        )
    elif isinstance(ca, str) and _OPTIONS_RE.match(ca):
        wrong_letters = [L for L in ("A", "B", "C", "D", "E") if L != ca]
        missing = [L for L in wrong_letters if L not in da]
        empty = [
            L for L in wrong_letters
            if L in da and not (isinstance(da[L], str) and da[L].strip())
        ]
        if missing:
            issues.append(
                f"`distractor_analysis` missing wrong-option keys: {missing}"
            )
        if empty:
            issues.append(
                f"`distractor_analysis` empty for wrong-option keys: {empty}"
            )

    # New fields validation (ESA-43)
    ds = obj.get("difficulty_score")
    if ds is not None:
        if not isinstance(ds, int) or ds < 1 or ds > 5:
            issues.append(f"`difficulty_score` must be an integer 1-5; got {ds!r}")
    else:
        issues.append("`difficulty_score` is missing (must be integer 1-5)")

    subj = obj.get("subject")
    if not isinstance(subj, str) or not subj.strip():
        issues.append("`subject` must be a non-empty string")

    hd = obj.get("has_diagram")
    if hd is not None and not isinstance(hd, bool):
        issues.append(f"`has_diagram` must be true/false; got {hd!r}")
    elif hd is None:
        issues.append("`has_diagram` is missing (must be true or false)")

    dd = obj.get("diagram_description")
    if dd is not None and not isinstance(dd, str):
        issues.append(f"`diagram_description` must be a string; got {type(dd).__name__}")
    elif dd is None:
        issues.append("`diagram_description` is missing (must be a string, empty if no diagram)")

    if issues:
        raise ValueError("Invalid question: " + "; ".join(issues))


# ──────────────────────────────────────────────────────────────────────────
# GLM-5.2 LLM client (z.ai OpenAI-compatible API)
# ──────────────────────────────────────────────────────────────────────────


@dataclass
class GenResult:
    text: str
    model: str
    cost_usd: float
    input_tokens: int
    output_tokens: int


def _quota_headroom_pct() -> Optional[float]:
    """Return weekly quota headroom in percent (elapsedPct - percentage).

    Positive = room available; negative = over pace. Returns None when the
    endpoint is unreachable so callers can fail open.
    """
    try:
        with urllib.request.urlopen(QUOTA_URL, timeout=5) as resp:
            data = json.loads(resp.read())
        weekly = data.get("weekly", {})
        used = float(weekly.get("percentage", 0))
        elapsed = float(weekly.get("elapsedPct", 0))
        return elapsed - used
    except Exception as exc:
        logger.debug("Quota endpoint unreachable (non-fatal): %s", exc)
        return None


def _quota_allows_generation() -> bool:
    """True if there is enough weekly headroom for one more question."""
    headroom = _quota_headroom_pct()
    if headroom is None:
        return True  # fail open when the guard is offline
    return headroom > QUOTA_HEADROOM_THRESHOLD_PCT


def call_glm(
    client: openai.OpenAI,
    *,
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = MAX_TOKENS,
) -> GenResult:
    """Call GLM-5.2 via z.ai OpenAI-compatible API with retry."""

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        if _shutdown:
            raise RuntimeError("Shutdown requested")

        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
                temperature=0.7,
            )

            text = response.choices[0].message.content or ""
            # Reasoning models put the real output in reasoning_content.
            # Fall back to it when content is empty or too short to parse.
            reasoning = getattr(
                response.choices[0].message, 'reasoning_content', None
            ) or ""
            if len(text.strip()) < 10 and reasoning.strip():
                text = reasoning
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            return GenResult(
                text=text,
                model=model,
                cost_usd=0.0,  # z.ai is free
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except openai.RateLimitError as exc:
            last_exc = exc
            delay = RETRY_BASE_DELAY * (2 ** attempt) + 1
            logger.warning(
                "Rate limit (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, delay, exc,
            )
            time.sleep(delay)

        except openai.APIConnectionError as exc:
            last_exc = exc
            delay = RETRY_BASE_DELAY * (2 ** attempt) + 1
            logger.warning(
                "Connection error (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, delay, exc,
            )
            time.sleep(delay)

        except openai.APIStatusError as exc:
            last_exc = exc
            if exc.status_code in (429, 500, 502, 503, 504):
                delay = RETRY_BASE_DELAY * (2 ** attempt) + 1
                logger.warning(
                    "Server error %d (attempt %d/%d), retrying in %.1fs",
                    exc.status_code, attempt + 1, MAX_RETRIES, delay,
                )
                time.sleep(delay)
            else:
                raise

    raise RuntimeError(f"GLM call failed after {MAX_RETRIES} attempts: {last_exc}")


# ──────────────────────────────────────────────────────────────────────────
# Public generate function
# ──────────────────────────────────────────────────────────────────────────


def generate(
    client: openai.OpenAI,
    spec_code: str,
    difficulty: str,
    *,
    model: str = DEFAULT_MODEL,
    seed: Optional[int] = None,
    patterns_dir: Path = PATTERNS_DIR,
) -> tuple[dict[str, Any], GenResult]:
    """Generate one ESAT question. Returns (question_dict, gen_result)."""
    bundle = load_pattern_bundle(spec_code, patterns_dir)

    # ESA-45 Part A: pull up to 4 real corpus exemplars for this exact
    # (topic, difficulty) cell and inject them as few-shot context.
    exemplars_block = ""
    exemplars_used = 0
    try:
        exs = exemplars.fetch_exemplars(spec_code, difficulty, seed=seed)
        exemplars_used = len(exs)
        exemplars_block = exemplars.render_exemplars_block(exs)
    except Exception as exc:  # never let exemplar lookup block generation
        logger.warning("exemplar fetch failed for %s: %s", spec_code, exc)

    user_prompt = render_user_prompt(bundle, difficulty, seed=seed,
                                     exemplars_block=exemplars_block)

    gen = call_glm(
        client,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=model,
    )
    parsed = parse_question(gen.text)

    # ESA-45 Part A: solution-first enforcement. The model opens the JSON with
    # a `_solution_commit` field (the Phase-0 derivation + COMMITTED ANSWER).
    # Move it into metadata (kept for forensics / downstream gates) and drop
    # the raw field so it is not stored as a student-visible column.
    commit = parsed.pop("_solution_commit", None)
    meta = parsed.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    if isinstance(commit, str) and commit.strip():
        meta["solution_commit"] = commit.strip()
    meta["solution_first"] = bool(isinstance(commit, str) and commit.strip())
    meta["exemplars_used"] = exemplars_used
    parsed["metadata"] = meta

    # Attach metadata (same as generator.py)
    parsed["module"] = spec_to_module(spec_code)
    parsed["spec_topic"] = spec_code
    parsed["source"] = "generated"
    parsed["generated_from_template_id"] = bundle.template_id
    parsed["difficulty"] = parsed.get("difficulty_band") or difficulty
    parsed["model"] = gen.model
    parsed["prompt_hash"] = hashlib.sha256(
        (SYSTEM_PROMPT + "\n\n" + user_prompt).encode("utf-8")
    ).hexdigest()

    # Fold distractor_analysis into metadata + append to explanation
    da = parsed.get("distractor_analysis")
    if isinstance(da, dict) and da:
        meta = parsed.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        meta["distractor_analysis"] = da
        parsed["metadata"] = meta

        ca = parsed.get("correct_answer", "")
        wrong_letters = [L for L in ("A", "B", "C", "D", "E") if L != ca]
        lines = [
            f"  - **{L}**: {da[L].strip()}"
            for L in wrong_letters
            if isinstance(da.get(L), str) and da[L].strip()
        ]
        if lines:
            parsed["explanation"] = (
                parsed["explanation"].rstrip()
                + "\n\n**Why the other options are wrong:**\n"
                + "\n".join(lines)
            )

    return parsed, gen


# ──────────────────────────────────────────────────────────────────────────
# Spec discovery
# ──────────────────────────────────────────────────────────────────────────


def discover_specs(patterns_dir: Path = PATTERNS_DIR) -> list[str]:
    specs: list[str] = []
    for d in sorted(patterns_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        children = [f.name for f in d.iterdir()]
        has_style = any(f.startswith("style_guide.") for f in children)
        has_distractor = any(f.startswith("distractor_catalogue.") for f in children)
        has_insight = any(f.startswith("insight_scenarios.") for f in children)
        if has_style and has_distractor and has_insight:
            specs.append(d.name)
    return specs


# ──────────────────────────────────────────────────────────────────────────
# Batch mode
# ──────────────────────────────────────────────────────────────────────────


def _build_coverage_queue(patterns_dir: Path, db_path: Path | None = None) -> list[tuple[str, str]]:
    """Build a queue of (spec_code, difficulty) using coverage tracker.

    Falls back to a random shuffle of all spec×difficulty combos if the
    coverage tracker has no targets (ESA-43).
    """
    import sqlite3 as _sqlite3
    import coverage_tracker as _ct

    specs = discover_specs(patterns_dir)
    if not specs:
        return []

    targets = _ct.load_targets()
    if not targets:
        # No coverage targets — fall back to random shuffle
        difficulties = list(VALID_DIFFICULTIES)
        queue = [(s, d) for s in specs for d in difficulties]
        random.shuffle(queue)
        logger.info("Coverage tracker has no targets — falling back to random shuffle (%d combos)", len(queue))
        return queue

    # Build coverage from DB (if available) or empty counts
    generated_counts: dict[tuple[str, str, str], int] = {}
    if db_path and db_path.exists():
        try:
            db = _sqlite3.connect(str(db_path))
            generated_counts = _ct._count_generated(db)
            db.close()
        except Exception as exc:
            logger.warning("Could not load generated counts from DB: %s", exc)

    coverage = _ct.compute_coverage(targets, generated_counts=generated_counts)

    # Build queue from sorted coverage (least-filled first)
    # Re-sort each pick so we always target the most under-represented cell
    remaining = [c for c in coverage if c.target_count > 0 and c.fill_ratio < 1.0]
    remaining.sort(key=lambda c: (c.fill_ratio, -c.shortfall, c.module, c.topic, c.difficulty))

    # Deduplicate to (topic, difficulty) tuples — coverage may have multiple
    # difficulty entries per topic. We want each unique combo once, ordered by
    # priority.
    queue: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for c in remaining:
        combo = (c.topic, c.difficulty)
        if combo not in seen and c.topic in specs:
            seen.add(combo)
            queue.append(combo)

    if not queue:
        # All cells at 100% — fall back to shuffle
        difficulties = list(VALID_DIFFICULTIES)
        queue = [(s, d) for s in specs for d in difficulties]
        random.shuffle(queue)
        logger.info("All coverage cells at 100%% — falling back to random shuffle (%d combos)", len(queue))
    else:
        logger.info("Coverage queue built: %d combos (from %d cells with shortfall)", len(queue), len(remaining))

    return queue


def run_batch(
    client: openai.OpenAI,
    *,
    model: str = DEFAULT_MODEL,
    output_dir: Path = OUTPUT_DIR,
    patterns_dir: Path = PATTERNS_DIR,
) -> int:
    """Cycle through specs × difficulties using coverage tracker. Returns count generated.

    Falls back to random shuffle when coverage tracker has no targets (ESA-43).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    specs = discover_specs(patterns_dir)
    if not specs:
        logger.error("No complete pattern bundles found in %s", patterns_dir)
        return 1

    db_path = SHARED_DIR / "data" / "questions.db"
    queue = _build_coverage_queue(patterns_dir, db_path)
    if not queue:
        logger.error("No generation queue built from coverage tracker or spec discovery")
        return 1

    logger.info("Batch mode: %d combos in queue (coverage-ordered)", len(queue))
    logger.info("Output dir: %s", output_dir)

    generated = 0
    errors = 0
    total_input_tokens = 0
    total_output_tokens = 0

    for i, (spec_code, difficulty) in enumerate(queue):
        if _shutdown:
            logger.info("Graceful shutdown — stopping after %d questions", generated)
            break

        # Per-question quota guard (ESA-40): stop the batch gracefully when
        # the weekly headroom drops below the safety threshold.
        headroom = _quota_headroom_pct()
        if headroom is not None and headroom <= QUOTA_HEADROOM_THRESHOLD_PCT:
            logger.warning(
                "Quota headroom %.2f%% ≤ %.2f%% threshold — stopping batch "
                "after %d questions to protect the weekly budget.",
                headroom, QUOTA_HEADROOM_THRESHOLD_PCT, generated,
            )
            break

        seed = random.randint(1, 2**31)
        filename = f"{spec_code}_{difficulty}_{seed}.json"
        filepath = output_dir / filename

        # Skip if already generated (resumable)
        if filepath.exists():
            logger.debug("[%d/%d] Skip (exists): %s", i + 1, len(queue), filename)
            continue

        try:
            question, gen_result = generate(
                client, spec_code, difficulty, model=model, seed=seed,
                patterns_dir=patterns_dir,
            )

            # Save to file
            output = {
                "question": question,
                "gen": {
                    "model": gen_result.model,
                    "cost_usd": gen_result.cost_usd,
                    "input_tokens": gen_result.input_tokens,
                    "output_tokens": gen_result.output_tokens,
                },
            }
            filepath.write_text(json.dumps(output, indent=2), encoding="utf-8")

            generated += 1
            total_input_tokens += gen_result.input_tokens
            total_output_tokens += gen_result.output_tokens

            if generated % 10 == 0 or generated <= 3:
                logger.info(
                    "[%d generated] %s / %s → %s (tokens=%d+%d) | errors=%d",
                    generated, spec_code, difficulty, filename,
                    gen_result.input_tokens, gen_result.output_tokens, errors,
                )

        except Exception as exc:
            errors += 1
            logger.error("Failed %s / %s: %s: %s", spec_code, difficulty, type(exc).__name__, exc)
            if errors > 30:
                logger.error("Too many errors (>30) — stopping.")
                break

        # Small delay between calls
        time.sleep(1.0)

    logger.info("=" * 60)
    logger.info("BATCH COMPLETE")
    logger.info("  Questions generated: %d", generated)
    logger.info("  Errors: %d", errors)
    logger.info("  Total tokens: %d input + %d output", total_input_tokens, total_output_tokens)
    logger.info("=" * 60)

    return generated


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT question generator (GLM-5.2 via z.ai)")
    p.add_argument("--spec-code", help="e.g. MATHS1.M1, PHYS.P5")
    p.add_argument("--difficulty", choices=VALID_DIFFICULTIES, help="Easy, Medium, or Hard")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL})")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--dry-run", action="store_true", help="Print the prompt, don't call the LLM")
    p.add_argument("--batch", action="store_true", help="Run batch mode (all specs × difficulties)")
    p.add_argument("--patterns-dir", type=Path, default=PATTERNS_DIR)
    p.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    p.add_argument("--api-key", help="z.ai API key (or set ZAI_API_KEY env var)")
    p.add_argument("--base-url", default=ZAI_BASE_URL, help=f"z.ai base URL (default: {ZAI_BASE_URL})")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # --- Dry run (no API key needed) ---
    if args.dry_run:
        if not args.spec_code or not args.difficulty:
            p.error("--spec-code and --difficulty required (or use --batch)")
        bundle = load_pattern_bundle(args.spec_code, args.patterns_dir)
        print("=== SYSTEM PROMPT ===")
        print(SYSTEM_PROMPT)
        print("\n=== USER PROMPT ===")
        print(render_user_prompt(bundle, args.difficulty, seed=args.seed))
        return 0

    # --- Batch or single mode ---
    if args.batch:
        api_key = resolve_api_key(args.api_key)
        if not api_key:
            print("ERROR: z.ai API key required. Set ZAI_API_KEY, pass --api-key, "
                  "or install the OpenClaw z.ai plugin.", file=sys.stderr)
            return 1
        client = openai.OpenAI(api_key=api_key, base_url=args.base_url)
        count = run_batch(client, model=args.model, output_dir=args.output_dir, patterns_dir=args.patterns_dir)
        print(f"\nDone. {count} questions generated.")
        return 0

    # --- Single mode ---
    if not args.spec_code or not args.difficulty:
        p.error("--spec-code and --difficulty required for single mode (or use --batch)")

    api_key = resolve_api_key(args.api_key)
    if not api_key:
        print("ERROR: z.ai API key required. Set ZAI_API_KEY, pass --api-key, "
              "or install the OpenClaw z.ai plugin.", file=sys.stderr)
        return 1

    # Quota guard: warn (do not block) — the user explicitly asked for one question.
    headroom = _quota_headroom_pct()
    if headroom is not None and headroom <= QUOTA_HEADROOM_THRESHOLD_PCT:
        logger.warning(
            "Quota headroom is %.2f%% (≤ %.2f%% threshold) — generating anyway "
            "because single-question mode was requested.",
            headroom, QUOTA_HEADROOM_THRESHOLD_PCT,
        )

    client = openai.OpenAI(api_key=api_key, base_url=args.base_url)

    question, gen = generate(
        client,
        args.spec_code,
        args.difficulty,
        model=args.model,
        seed=args.seed,
        patterns_dir=args.patterns_dir,
    )
    out = {
        "question": question,
        "gen": {
            "model": gen.model,
            "cost_usd": gen.cost_usd,
            "input_tokens": gen.input_tokens,
            "output_tokens": gen.output_tokens,
        },
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
