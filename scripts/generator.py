#!/usr/bin/env python3
"""
ESAT question generator — ESA-17 §2.4 + §4 item 6.

Primary model: Gemini 2.5 Flash (free via Google AI, 250 RPD).
Fallback: Gemini 2.5 Pro (free via Google AI, 50 RPD).

The generator loads the Opus-produced per-topic pattern bundle
(`style_guide.<spec>.md`, `distractor_catalogue.<spec>.json`,
`insight_scenarios.<spec>.json`) from `shared/patterns/<SPEC_CODE>/` and
renders a single prompt that enforces the ESAT calculator-free constraints:
g = 10 m/s², standard angles only, 5 options A–E, integer-friendly arithmetic.

Output: a question dict matching the `questions` table schema (see
`src/lib/db.ts`). The dict is ready to drop into `generation_attempts` or
the website query path.

Usage:
    python3 generator.py --spec-code MATHS1.M1 --difficulty Easy
    python3 generator.py --spec-code PHYS.P5 --difficulty Hard
    python3 generator.py --spec-code CHEM.C4 --dry-run

Environment:
    GEMINI_API_KEY  — required for the Google Gemini SDK

Reference: ESA-17 plan §4.4, strategy §2.4 + §4 item 6 + §10.2,
`orchestration-review.md` Priorities #4 + #7.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Make sibling `quality/` importable when run as a script.
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from google import genai
    from google.genai.types import GenerateContentConfig, Part
except ImportError:  # pragma: no cover
    genai = None  # type: ignore

try:
    import anthropic  # type: ignore
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore

try:
    import openai  # type: ignore
except ImportError:  # pragma: no cover
    openai = None  # type: ignore

# ESA-45 Part A: corpus few-shot exemplars (sibling module).
try:
    import exemplars as _exemplars  # type: ignore
except ImportError:  # pragma: no cover
    _exemplars = None  # type: ignore


logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────

PATTERNS_DIR = Path(__file__).resolve().parent.parent / "patterns"

# Primary API key from environment; fallback provided if quota exhausted.
PRIMARY_API_KEY = os.environ.get("GEMINI_API_KEY")
FALLBACK_API_KEY = "AIzaSyBkiGJSS45VVKwZuTL6oXPl-K3_Qv9z-44"  # Provided 2026-07-20

# Gemini 2.5 Flash is the primary generation model (free tier: 250 RPD).
# Gemini 2.5 Pro is the fallback (free tier: 50 RPD). Both via Google AI.
# We track token usage for the cost log even though the free tier is $0.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.0, "output": 0.0},  # free tier
    "gemini-2.5-pro": {"input": 0.0, "output": 0.0},     # free tier
    # Paid tier pricing (if quota exhausted)
    "gemini-2.5-flash-paid": {"input": 0.30, "output": 2.40},
    "gemini-2.5-pro-paid": {"input": 1.25, "output": 10.0},
    # Legacy GLM pricing (kept for reference)
    "glm-5.2": {"input": 0.0, "output": 0.0},
    "glm-4.5-air": {"input": 0.0, "output": 0.0},
}

PRIMARY_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-2.5-pro"

# Legacy z.ai base URL (kept for backward compat, unused with Gemini)
ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"

MAX_RETRIES = 4
RETRY_BASE_DELAY = 1.5  # seconds; doubled per retry
# After this many consecutive 429s on the primary model, switch to fallback.
RATE_LIMIT_FALLBACK_THRESHOLD = 2


def _is_quota_error(exc: Exception) -> bool:
    """Check if exception is a quota/rate-limit error (429)."""
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    if status == 429:
        return True
    msg = str(exc).lower()
    if "quota exceeded" in msg or "resource_exhausted" in msg:
        return True
    return False

MAX_TOKENS = 4096

# Module code → DB module string. Pattern dirs use MATHS1.M1 / PHYS.P5 etc.;
# the questions table stores lowercase module names.
SPEC_PREFIX_TO_MODULE: dict[str, str] = {
    "MATHS1": "maths1",
    "MATHS2": "maths2",
    "PHYS": "physics",
    "CHEM": "chemistry",
    "BIO": "biology",
}

VALID_DIFFICULTIES = ("Easy", "Medium", "Hard", "Very Hard")


# ──────────────────────────────────────────────────────────────────────────
# Pattern loading
# ──────────────────────────────────────────────────────────────────────────


def spec_to_module(spec_code: str) -> str:
    """MATHS1.M1 → maths1, PHYS.P5 → physics, etc."""
    prefix = spec_code.split(".", 1)[0].upper()
    if prefix not in SPEC_PREFIX_TO_MODULE:
        raise ValueError(
            f"Unknown spec prefix {prefix!r} (from {spec_code!r}). "
            f"Known: {sorted(SPEC_PREFIX_TO_MODULE)}"
        )
    return SPEC_PREFIX_TO_MODULE[prefix]


@dataclass
class PatternBundle:
    """The three Opus-produced pattern files for one spec topic."""

    spec_code: str
    style_guide: str
    distractor_catalogue: dict[str, Any]
    insight_scenarios: dict[str, Any]
    base_dir: Path

    @property
    def template_id(self) -> str:
        """Stable identifier for this pattern bundle version.

        Currently the mtime of the style guide — bumped whenever Opus
        re-extracts. Stored on `questions.generated_from_template_id` so
        the concept-level dedup cap can limit clones of one template.
        """
        try:
            return f"{self.spec_code}:{int(self.base_dir.stat().st_mtime)}"
        except OSError:
            return self.spec_code


def load_pattern_bundle(spec_code: str, patterns_dir: Path = PATTERNS_DIR) -> PatternBundle:
    """Load the three pattern files for a spec code.

    Raises FileNotFoundError if the bundle is missing — the caller should
    skip the spec code and log a coverage gap.
    """
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
# Prompt rendering
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
    """Render the per-question user prompt from the pattern bundle.

    The prompt is deterministic given (spec_code, difficulty, seed,
    exemplars) so two models given the same prompt produce directly
    comparable A/B output (ESA-26 Part A requirement).

    `exemplars_block` is the rendered few-shot block of real corpus
    questions (ESA-45 Part A) — injected when available. Empty string
    means no matching exemplars were found for this cell.
    """
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {VALID_DIFFICULTIES}; got {difficulty!r}")

    # Pull 2 distractor strategies + 1 insight scenario deterministically.
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
    exemplars_section = f"\n{exemplars_block}\n" if exemplars_block else ""

    return f"""## SPEC CODE
{bundle.spec_code}

## TARGET DIFFICULTY
{difficulty}

## STYLE GUIDE (Opus-extracted from corpus)
{bundle.style_guide}

## DISTRACTOR PATTERNS (use at least 2)
{distractor_block}

## INSIGHT SCENARIOS (use 1 as the conceptual spine)
{scenario_block}{exemplars_section}{seed_line}

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
# LLM client wrappers
# ──────────────────────────────────────────────────────────────────────────


@dataclass
class GenResult:
    """One LLM generation call's outcome."""

    text: str
    model: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    fell_back: bool  # True if we switched from primary → fallback


def _estimate_cost(model: str, usage: Any) -> float:
    p = MODEL_PRICING.get(
        model, {"input": 0.30, "output": 2.40}
    )
    # Support both attribute-style (Usage) and simple objects
    inp = getattr(usage, "input_tokens", 0) or getattr(usage, "prompt_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or getattr(usage, "completion_tokens", 0) or 0
    return inp * p["input"] / 1_000_000 + out * p["output"] / 1_000_000


def _call_gemini(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = MAX_TOKENS,
) -> tuple[str, float, int, int]:
    """Call Google Gemini via the google-genai SDK.

    Uses native JSON mode (response_mime_type='application/json') which
    eliminates the need for fence-stripping heuristics in parse_question().

    Returns (text, cost_usd, input_tokens, output_tokens).
    """
    if genai is None:
        raise RuntimeError(
            "google-genai SDK not installed — run `pip install google-genai`"
        )
    api_key = PRIMARY_API_KEY or FALLBACK_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=0.7,
            response_mime_type="application/json",
        ),
    )

    text = response.text or ""

    # Extract token usage from the response metadata.
    usage = getattr(response, "usage_metadata", None)
    input_tokens = getattr(usage, "prompt_token_count", 0) or 0 if usage else 0
    output_tokens = getattr(usage, "candidates_token_count", 0) or 0 if usage else 0

    cost = _estimate_cost(model, type("Usage", (), {"input_tokens": input_tokens, "output_tokens": output_tokens})())
    return text, cost, input_tokens, output_tokens


def call_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str = PRIMARY_MODEL,
    max_tokens: int = MAX_TOKENS,
) -> GenResult:
    """Call the LLM with exponential backoff + automatic fallback.

    On `RATE_LIMIT_FALLBACK_THRESHOLD` consecutive rate-limit errors on the
    primary model, switch to FALLBACK_MODEL for the actual generation.
    """
    call = _call_gemini

    consecutive_429 = 0
    last_exc: Optional[Exception] = None
    fell_back = False
    active_model = model

    for attempt in range(MAX_RETRIES):
        try:
            text, cost, inp, out = call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=active_model,
                max_tokens=max_tokens,
            )
            return GenResult(
                text=text,
                model=active_model,
                cost_usd=cost,
                input_tokens=inp,
                output_tokens=out,
                fell_back=fell_back,
            )
        except Exception as exc:  # noqa: BLE001 — broad: we retry any transient error
            last_exc = exc
            is_rate_limit = _is_rate_limit(exc)
            if is_rate_limit:
                consecutive_429 += 1
                if (
                    consecutive_429 >= RATE_LIMIT_FALLBACK_THRESHOLD
                    and active_model != FALLBACK_MODEL
                ):
                    logger.warning(
                        "Primary model %s rate-limited %d× — switching to fallback %s",
                        active_model, consecutive_429, FALLBACK_MODEL,
                    )
                    active_model = FALLBACK_MODEL
                    fell_back = True
                    consecutive_429 = 0
                    continue
            delay = RETRY_BASE_DELAY * (2 ** attempt) + 0.5
            logger.warning(
                "LLM call failed (attempt %d/%d, model=%s, rate_limit=%s); "
                "retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, active_model, is_rate_limit,
                delay, exc,
            )
            time.sleep(delay)

    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts: {last_exc}")


def _is_rate_limit(exc: Exception) -> bool:
    """Heuristic — works across anthropic + openai SDKs."""
    name = type(exc).__name__
    if "RateLimit" in name:
        return True
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status == 429:
        return True
    msg = str(exc).lower()
    # Substring heuristics — match actual API wording, not arbitrary prose
    # that happens to contain the words (e.g. "not a rate limit").
    if "rate limit exceeded" in msg:
        return True
    if "rate_limit_exceeded" in msg:
        return True
    if "too many requests" in msg:
        return True
    # Anthropic/z.ai returns 503 "overloaded" — treat as transient rate-limit.
    if "overloaded" in msg or "overloaded_error" in msg:
        return True
    if "429" in msg:
        return True
    return False


# ──────────────────────────────────────────────────────────────────────────
# Output parsing + validation
# ──────────────────────────────────────────────────────────────────────────


_OPTIONS_RE = re.compile(r"^[A-E]$")


def parse_question(text: str) -> dict[str, Any]:
    """Extract the JSON question object from the LLM response.

    The model occasionally wraps JSON in ```json fences despite the
    "output only JSON" instruction — we strip those defensively.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip opening fence (with optional `json` label) and closing fence.
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    # Find the first { ... } block if there's leading/trailing prose.
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
    """Check the question dict has the required fields with correct types.

    Raises ValueError with a human-readable list of issues.

    Required: question_text, options (A–E), correct_answer (A–E),
    explanation, distractor_analysis (object keyed by the four wrong
    letters), and the ESA-45 solution-first `_solution_commit` field (the
    hidden Phase-0 derivation + COMMITTED ANSWER). The `_solution_commit`
    requirement is the hard structural enforcement of solution-first
    generation; the distractor_analysis requirement enforces the Phase-3
    tail — its absence signals the model skipped a step.
    """
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

    # STEP-4 enforcement: distractor_analysis must be present and cover
    # exactly the four wrong letters. We do not fail on extra keys
    # (some models echo `correct_answer` as a key with "Correct." — we
    # only require that all four wrong letters are present and non-empty).
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

    if issues:
        raise ValueError("Invalid question: " + "; ".join(issues))


# ──────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────


def generate(
    spec_code: str,
    difficulty: str,
    *,
    model: str = PRIMARY_MODEL,
    seed: Optional[int] = None,
    patterns_dir: Path = PATTERNS_DIR,
) -> tuple[dict[str, Any], GenResult]:
    """Generate one ESAT question for the given spec code + difficulty.

    Returns (question_dict, gen_result). The question_dict matches the
    `questions` table schema and is ready to drop into
    `generation_attempts` / the website query path.
    """
    bundle = load_pattern_bundle(spec_code, patterns_dir)

    # ESA-45 Part A: pull up to 4 real corpus exemplars for this exact
    # (topic, difficulty) cell and inject them as few-shot context.
    exemplars_block = ""
    exemplars_used = 0
    if _exemplars is not None:
        try:
            exs = _exemplars.fetch_exemplars(spec_code, difficulty, seed=seed)
            exemplars_used = len(exs)
            exemplars_block = _exemplars.render_exemplars_block(exs)
        except Exception as exc:  # never let exemplar lookup block generation
            logger.warning("exemplar fetch failed for %s: %s", spec_code, exc)

    user_prompt = render_user_prompt(bundle, difficulty, seed=seed,
                                     exemplars_block=exemplars_block)

    gen = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=model,
    )
    parsed = parse_question(gen.text)

    # ESA-45 Part A: solution-first enforcement. The model is required to
    # open the JSON with a `_solution_commit` field (the hidden Phase-0
    # derivation + COMMITTED ANSWER). Move it into metadata (kept for
    # forensics / downstream gates) and remove the raw field so it is not
    # stored as a student-visible column.
    commit = parsed.pop("_solution_commit", None)
    meta = parsed.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    if isinstance(commit, str) and commit.strip():
        meta["solution_commit"] = commit.strip()
    meta["solution_first"] = bool(isinstance(commit, str) and commit.strip())
    meta["exemplars_used"] = exemplars_used
    parsed["metadata"] = meta

    # Attach metadata so downstream gates + dedup can use it without
    # re-deriving from the spec code.
    parsed["module"] = spec_to_module(spec_code)
    parsed["spec_topic"] = spec_code
    parsed["source"] = "generated"
    parsed["generated_from_template_id"] = bundle.template_id
    parsed["difficulty"] = parsed.get("difficulty_band") or difficulty
    parsed["model"] = gen.model
    parsed["prompt_hash"] = hashlib.sha256(
        (SYSTEM_PROMPT + "\n\n" + user_prompt).encode("utf-8")
    ).hexdigest()

    # The strict CoT flow produces a `distractor_analysis` object (STEP 4).
    # The `questions` table has no dedicated column for it, so we:
    #   (a) fold it into `metadata.distractor_analysis` for downstream
    #       gates / dedup / website rendering, and
    #   (b) append a compact "Why each wrong option is wrong" block to
    #       `explanation` so the worked solution a student sees includes
    #       the distractor takeaways (matches ESAT past-paper style).
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
# CLI
# ──────────────────────────────────────────────────────────────────────────


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate one ESAT question")
    p.add_argument("--spec-code", required=True, help="e.g. MATHS1.M1, PHYS.P5")
    p.add_argument("--difficulty", required=True, choices=VALID_DIFFICULTIES)
    p.add_argument("--model", default=PRIMARY_MODEL)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--dry-run", action="store_true", help="Print the prompt, don't call the LLM")
    p.add_argument("--patterns-dir", type=Path, default=PATTERNS_DIR)
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.dry_run:
        bundle = load_pattern_bundle(args.spec_code, args.patterns_dir)
        print("=== SYSTEM PROMPT ===")
        print(SYSTEM_PROMPT)
        print("\n=== USER PROMPT ===")
        print(render_user_prompt(bundle, args.difficulty, seed=args.seed))
        return 0

    question, gen = generate(
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
            "fell_back": gen.fell_back,
        },
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
