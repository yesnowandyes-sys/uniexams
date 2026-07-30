#!/usr/bin/env python3
"""
GLM (z.ai) API Enrichment Pipeline for ESAT Questions.

Companion to anthropic-enrichment.py — identical prompts, validation, and
output format, but calls the z.ai OpenAI-compatible API instead of Anthropic.

Usage:
    python glm-enrichment.py --input corpus/json/esat/esat_specimen_physics.json
    python glm-enrichment.py --input corpus/json/ --limit 5
    python glm-enrichment.py --dry-run --limit 3
    python glm-enrichment.py --model glm-5.2 --limit 10

Environment:
    ZAI_API_KEY  — Required. z.ai API key.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import openai


# ---------------------------------------------------------------------------
# Diagram detection helper
# ---------------------------------------------------------------------------


def question_has_diagram(question: dict[str, Any]) -> bool:
    """Check if a question has diagram images attached."""
    if question.get("has_diagram", False):
        return True
    if question.get("diagram_images"):
        return True
    if question.get("question_images"):
        return True
    return False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus" / "json"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "enriched-output" / "glm-trial"

ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"

# z.ai is free — cost is always $0.00
MODEL_PRICING: dict[str, dict[str, float]] = {
    "glm-5.2": {"input": 0.0, "output": 0.0},
}

DEFAULT_MODEL = "glm-5.2"

MAX_RETRIES = 5
RETRY_BASE_DELAY = 2.0  # seconds, doubled on each retry

MAX_TOKENS = 32768

# ---------------------------------------------------------------------------
# System prompt (static — identical to Anthropic script)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert Cambridge admissions test analyst specialising in the \
Engineering and Science Admissions Test (ESAT). You have deep knowledge of \
the ESAT Content Specification across Mathematics, Physics, Chemistry, and \
Biology modules. Your task is to analyse past paper questions and produce \
structured enrichment data for each one.

## NUMERICAL CONVENTIONS

- Gravitational field strength: g = 10 N kg⁻¹ (always — this is the ESAT \
  convention, stated in specification P3.5b). Do NOT use g = 9.81 or g = 9.8.
- When a question involves gravity and does not state a value for g, use g = 10.
- Use only standard angles: 0°, 30°, 45°, 60°, 90° (and multiples).
- All specific heat capacities, latent heats, and physical constants not \
  listed here MUST be given in the question stem.

## CONTEXT: ESAT CONTENT SPECIFICATION TAXONOMY

{esat_taxonomy_for_module}

The taxonomy above defines the module, subtopics, and content codes for the \
relevant ESAT subject area. Use these exact codes when classifying the question.

## NSAA S2 OUT-OF-SPEC FILTERING

{nsaa_s2_filtering_rule}

If the filtering rule above is ACTIVE for this question:
1. Classify the topic FIRST, before any other work.
2. If the topic cannot be mapped to any entry in the ESAT taxonomy above, \
   the question is out-of-spec. Produce ONLY the Classification section \
   with Content Code set to OUT_OF_SPEC, and a brief note explaining why \
   the topic is outside the ESAT syllabus. Do NOT generate a Worked Solution \
   or Distractor Analysis.
3. If the topic CAN be mapped to the taxonomy, proceed with full enrichment.

## OUTPUT FORMAT

Write your response in Markdown format. Use LaTeX notation \
($...$ for inline, $$...$$ for display) for all mathematical symbols, \
fractions, equations, and Greek letters. Use Markdown headers (##, ###), \
bullet lists, and bold text for structure.

### Structure your response as follows:

## Worked Solution

Provide a complete, step-by-step solution showing all working. Use \
numbered lists for steps and LaTeX for all mathematical expressions. \
Each step should be clear enough for a student to follow without \
additional explanation.

**CRITICAL: The written solution must be fully self-contained.** \
Do not rely on any diagram to convey essential reasoning. A student \
reading only the text should be able to follow the complete solution. \
Diagrams are supplementary visual aids only — they do not replace \
any part of the written explanation.

**Diagram markers:** If a diagram would help illustrate a step or \
concept in the solution, place a marker on its own line at the point \
where the diagram would appear:

[DIAGRAM 1]
[DIAGRAM 2]
etc. (up to 4 diagrams maximum per question)

Continue the written solution immediately after the marker. The \
text before and after the marker must flow naturally without the \
diagram being present.

Only place [DIAGRAM n] markers if a diagram image was provided with the question. If no diagram image was provided, do NOT place any diagram markers.

## Distractor Analysis

For each incorrect option, explain precisely why it is wrong. \
Identify the common misconception or calculation error that would lead \
a student to choose that answer. The number of distractors corresponds \
to the number of options provided — not always 4.

## Classification

- **Module:** (e.g., Mathematics 2, Physics)
- **Subtopic:** (e.g., Kinematics, Algebra)
- **Content Code:** (from the ESAT taxonomy provided, or OUT_OF_SPEC)
- **Question Type:** (e.g., single-step calculation, multi-step \
  derivation, conceptual)

## Difficulty Rating

Rate the difficulty on a scale of 1-10, where 1 is straightforward and \
10 is extremely challenging for a strong ESAT candidate. Briefly justify \
the rating.

**Difficulty:** X/10

**FINAL STEP:** Always end your worked solution with an explicit conclusion that maps your calculated result back to the correct option letter. Format: "The correct answer is **X**." where X is the option letter (A, B, C, etc.).

## Diagram Descriptions

For each [DIAGRAM n] marker placed in the worked solution, provide a \
description of what that diagram should show when it is eventually \
generated. If no diagrams would add value, write:

No diagrams needed.

**IMPORTANT:** If the question does not include a diagram image (no diagram was provided in the input), you MUST write exactly "No diagrams needed." Do not generate [DIAGRAM n] markers in the worked solution or describe diagrams in this section. Diagrams are ONLY for questions where a diagram image was explicitly provided.

Otherwise, for each diagram:

### Diagram 1
**Type:** (e.g., free-body diagram, circuit diagram, graph, sketch)
**Content:** Describe exactly what the diagram should depict — all \
labels, values, axes, components, and spatial relationships.
**Purpose:** What concept or step does this diagram illustrate?"""

# ---------------------------------------------------------------------------
# User prompt templates (identical to Anthropic script)
# ---------------------------------------------------------------------------

USER_PROMPT_TEMPLATE = """\
Produce a complete enrichment for this question using the output format \
specified in your system instructions.

### Question
{question_text}

### Options
{options_list}
(Note: the number of options varies per question — typically 4 to 8, \
not always A–E. Biology questions commonly have 6 or 8 options.)

### Correct Answer
{correct_answer_letter}"""

USER_PROMPT_DIAGRAM_TEMPLATE = """\
Produce a complete enrichment for this question using the output format \
specified in your system instructions.

### Question
{question_text}

### Options
{options_list}
(Note: the number of options varies per question — typically 4 to 8, \
not always A–E. Biology questions commonly have 6 or 8 options.)

### Correct Answer
{correct_answer_letter}

### Diagram
{diagram_content}"""

# ---------------------------------------------------------------------------
# Out-of-spec topics for NSAA S2 filtering (identical)
# ---------------------------------------------------------------------------

OUT_OF_SPEC_PATTERNS: list[str] = [
    "quantum physics", "photoelectric effect", "energy levels", "photon",
    "binding energy", "nuclear stability", "gravitational field",
    "gravitational potential", "magnetic field", "electromagnetic induction",
    "organic synthesis", "multi-step mechanism", "gibbs free energy",
    "entropy", "electrode potential", "electrochemical cell",
    "transition metal", "epigenetic", "gene regulation",
    "neuroscience", "nerve impulse", "ecosystem ecology", "succession",
    "nutrient cycle",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("glm-enrichment")

# ---------------------------------------------------------------------------
# Data classes (identical)
# ---------------------------------------------------------------------------


@dataclass
class EnrichmentResult:
    """Result of enriching a single question."""

    question_id: str
    status: str  # "success", "skipped", "failed", "out_of_spec"
    enrichment_markdown: str = ""
    error: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    duration_seconds: float = 0.0
    verification_verified: bool = True
    verification_issues: list[str] = field(default_factory=list)


@dataclass
class CorpusFile:
    """A single corpus JSON file and its metadata."""

    path: Path
    source_type: str  # esat, engaa, nsaa, nsaa_s2, tmua
    section: Optional[str] = None
    subject: Optional[str] = None
    module: Optional[str] = None


# ---------------------------------------------------------------------------
# Corpus loading (identical)
# ---------------------------------------------------------------------------


def detect_corpus_file(path: Path) -> CorpusFile:
    """Detect the corpus file type from its path."""
    parts = path.relative_to(CORPUS_DIR).parts
    source_type = parts[0] if parts else "unknown"

    section = None
    subject = None
    module = None

    if source_type == "esat":
        module = path.stem.replace("esat_specimen_", "")
    elif source_type == "engaa":
        section = "S1"
    elif source_type == "tmua":
        name = path.stem
        parts2 = name.split("_", 1)
        if len(parts2) == 2:
            section = parts2[1].upper()
    elif source_type == "nsaa_s2":
        section = "S2"
        name = path.stem
        if "physics" in name:
            subject = "physics"
        elif "chemistry" in name:
            subject = "chemistry"
        elif "biology" in name:
            subject = "biology"
    elif source_type == "nsaa":
        section = "S1"

    return CorpusFile(
        path=path,
        source_type=source_type,
        section=section,
        subject=subject,
        module=module,
    )


def resolve_input_path(input_path: Path) -> Path:
    """Resolve input path against corpus dir or CWD."""
    if input_path.is_absolute() and input_path.exists():
        return input_path
    cwd_candidate = Path.cwd() / input_path
    if cwd_candidate.exists():
        return cwd_candidate.resolve()
    corpus_candidate = CORPUS_DIR / input_path
    if corpus_candidate.exists():
        return corpus_candidate
    return input_path.resolve()


def load_corpus_files(input_path: Path) -> list[CorpusFile]:
    """Load all corpus JSON files from a path (file or directory)."""
    files: list[CorpusFile] = []

    resolved = resolve_input_path(input_path)

    if resolved.is_file() and resolved.suffix == ".json":
        files.append(detect_corpus_file(resolved))
    elif resolved.is_dir():
        for json_file in sorted(resolved.rglob("*.json")):
            files.append(detect_corpus_file(json_file))
    else:
        logger.error("Input path %s is not a valid file or directory", input_path)
        sys.exit(1)

    logger.info("Found %d corpus file(s)", len(files))
    return files


def load_questions_from_file(corpus_file: CorpusFile) -> list[dict[str, Any]]:
    """Load questions array from a corpus JSON file."""
    with open(corpus_file.path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "questions" in data:
        return data["questions"]
    elif isinstance(data, list):
        return data
    else:
        logger.error("Unexpected format in %s", corpus_file.path)
        return []


# ---------------------------------------------------------------------------
# Prompt building (identical)
# ---------------------------------------------------------------------------


def get_nsaa_s2_filtering_rule(corpus_file: CorpusFile) -> str:
    """Return the NSAA S2 filtering rule text based on file type."""
    if corpus_file.source_type == "nsaa_s2":
        return (
            "ACTIVE — This is an NSAA Section 2 question. "
            "Classify the topic first. If the topic cannot be mapped to "
            "the ESAT taxonomy above, mark as OUT_OF_SPEC and skip the "
            "Worked Solution and Distractor Analysis."
        )
    return "INACTIVE — Full enrichment required for all questions."


def format_options(options: dict[str, str]) -> str:
    """Format options dict into a readable list."""
    lines = []
    for letter, text in options.items():
        lines.append(f"- {letter}: {text}")
    return "\n".join(lines)


def build_system_prompt(corpus_file: CorpusFile, esat_taxonomy: str) -> str:
    """Build the full system prompt for a question."""
    return SYSTEM_PROMPT.format(
        esat_taxonomy_for_module=esat_taxonomy,
        nsaa_s2_filtering_rule=get_nsaa_s2_filtering_rule(corpus_file),
    )


def build_user_prompt(question: dict[str, Any], corpus_file: CorpusFile) -> str:
    """Build the user prompt for a specific question."""
    question_text = question.get("question_text", "")
    options = question.get("options", {})
    correct_answer = question.get("correct_answer", "")
    if not correct_answer:
        correct_answer = question.get("correct_answer_plain", "")

    options_list = format_options(options)

    diagram_images = question.get("diagram_images", []) or question.get("question_images", [])

    if diagram_images:
        diagram_lines = []
        for i, img_path in enumerate(diagram_images):
            diagram_lines.append(f"Diagram {i+1}: [Image path: {img_path}]")
        diagram_content = "\n".join(diagram_lines)

        return USER_PROMPT_DIAGRAM_TEMPLATE.format(
            question_text=question_text,
            options_list=options_list,
            correct_answer_letter=correct_answer,
            diagram_content=diagram_content,
        )

    return USER_PROMPT_TEMPLATE.format(
        question_text=question_text,
        options_list=options_list,
        correct_answer_letter=correct_answer,
    )


def resolve_taxonomy_context(corpus_file: CorpusFile) -> str:
    """Resolve which ESAT taxonomy modules are relevant for this corpus file."""
    source = corpus_file.source_type

    if source == "esat":
        mod = corpus_file.module or "unknown"
        return (
            f"Module: {mod.capitalize()} (ESAT Specimen)\n\n"
            f"Note: This question is from the ESAT specimen paper, module {mod}. "
            f"Classify using the standard ESAT {mod.capitalize()} content specification "
            f"taxonomy (topics, subtopics, and content codes as defined in the "
            f"official ESAT Content Specification)."
        )

    elif source == "tmua":
        section = corpus_file.section or ""
        if "P1" in section:
            return (
                "Module: Mathematics 1 (TMUA Paper 1)\n\n"
                "Note: This question is from a TMUA Paper 1 past paper. "
                "Classify using the ESAT Mathematics 1 content specification "
                "taxonomy."
            )
        else:
            return (
                "Module: Mathematics 2 (TMUA Paper 2)\n\n"
                "Note: This question is from a TMUA Paper 2 past paper. "
                "Classify using the ESAT Mathematics 2 content specification "
                "taxonomy."
            )

    elif source == "engaa":
        return (
            "Modules: Mathematics 1 + Mathematics 2 (ENGAA Section 1)\n\n"
            "Note: This question is from an ENGAA Section 1 past paper, "
            "which covers both Mathematics 1 and Mathematics 2 content. "
            "Classify using both ESAT M1 and M2 taxonomies."
        )

    elif source == "nsaa":
        return (
            "Modules: Physics + Chemistry + Biology (NSAA Section 1)\n\n"
            "Note: This question is from an NSAA Section 1 past paper. "
            "Classify using the appropriate ESAT subject taxonomy "
            "(Physics, Chemistry, or Biology) based on the question content."
        )

    elif source == "nsaa_s2":
        subj = corpus_file.subject or "unknown"
        return (
            f"Module: {subj.capitalize()} (NSAA Section 2)\n\n"
            f"Note: This question is from an NSAA Section 2 {subj} paper. "
            f"NSAA S2 extends beyond the ESAT specification — classify against "
            f"the ESAT {subj.capitalize()} content specification taxonomy. "
            f"Topics that cannot be mapped to the ESAT taxonomy are out-of-spec."
        )

    return "Module: Unknown — classify based on question content."


# ---------------------------------------------------------------------------
# API calling — OpenAI-compatible (z.ai)
# ---------------------------------------------------------------------------


def _encode_image_as_data_uri(abs_path: str) -> Optional[str]:
    """Encode an image file as a base64 data URI for the OpenAI vision format."""
    if not os.path.exists(abs_path):
        logger.warning("Diagram image not found: %s", abs_path)
        return None

    ext = Path(abs_path).suffix.lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/png")

    with open(abs_path, "rb") as img_f:
        img_data = base64.standard_b64encode(img_f.read()).decode("utf-8")

    return f"data:{media_type};base64,{img_data}"


def call_glm_api(
    client: openai.OpenAI,
    system_prompt: str,
    user_prompt: str,
    model: str,
    image_paths: Optional[list[str]] = None,
) -> tuple[str, dict[str, int]]:
    """
    Call the z.ai OpenAI-compatible API with retry logic.

    Returns (response_text, token_usage_dict).
    Raises RuntimeError after exhausting retries.
    """
    # Build user message content blocks
    content_blocks: list[dict[str, Any]] = []

    if image_paths:
        # Try to encode images for vision; gracefully degrade if any fail
        vision_images = []
        text_only = False
        for img_path in image_paths:
            abs_path = img_path if os.path.isabs(img_path) else str(CORPUS_DIR.parent / "images" / img_path)
            data_uri = _encode_image_as_data_uri(abs_path)
            if data_uri:
                vision_images.append(data_uri)
            # else: logged by _encode_image_as_data_uri

        if vision_images:
            # Send multimodal content
            # Text part first
            content_blocks.append({"type": "text", "text": user_prompt})
            # Image parts
            for data_uri in vision_images:
                content_blocks.append({
                    "type": "image_url",
                    "image_url": {"url": data_uri, "detail": "auto"},
                })
        else:
            # All images failed to load — fall back to text only
            logger.warning("No images could be loaded; sending text-only prompt")
            content_blocks.append({"type": "text", "text": user_prompt})
    else:
        content_blocks.append({"type": "text", "text": user_prompt})

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content_blocks},
    ]

    last_exception: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": MAX_TOKENS,
                "messages": messages,
            }

            response = client.chat.completions.create(**kwargs)

            # Extract text from response
            response_text = response.choices[0].message.content or ""

            # Token usage
            usage = response.usage
            token_usage = {
                "input_tokens": usage.prompt_tokens if usage else 0,
                "output_tokens": usage.completion_tokens if usage else 0,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
            }

            return response_text, token_usage

        except openai.RateLimitError as e:
            last_exception = e
            delay = RETRY_BASE_DELAY * (2 ** attempt) + 1
            logger.warning(
                "Rate limit hit (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, delay, e,
            )
            time.sleep(delay)

        except openai.APIConnectionError as e:
            last_exception = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Connection error (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, delay, e,
            )
            time.sleep(delay)

        except openai.APIStatusError as e:
            if 400 <= e.status_code < 500 and e.status_code != 429:
                # Special handling: if the endpoint doesn't support vision,
                # retry without images
                if e.status_code == 400 and image_paths and "image" in str(e).lower():
                    logger.warning(
                        "Vision API not supported (attempt %d/%d), falling back to text-only",
                        attempt + 1, MAX_RETRIES,
                    )
                    # Retry without images
                    return call_glm_api(
                        client=client,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model=model,
                        image_paths=None,
                    )
                raise RuntimeError(f"API error {e.status_code}: {e.message}") from e
            last_exception = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "API error (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, delay, e,
            )
            time.sleep(delay)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries: {last_exception}")


# ---------------------------------------------------------------------------
# Output parsing / validation (identical)
# ---------------------------------------------------------------------------


def validate_enrichment(text: str) -> dict[str, Any]:
    """
    Parse the enrichment markdown into structured sections.

    Returns a dict with keys: worked_solution, distractor_analysis,
    classification, difficulty_rating, diagram_descriptions.
    """
    sections: dict[str, str] = {}

    pattern = r"^##\s+(.+)$"
    parts = re.split(pattern, text, flags=re.MULTILINE)

    current_section = None
    for i, part in enumerate(parts):
        if i % 2 == 1:
            current_section = part.strip().lower()
        else:
            if current_section:
                sections[current_section] = part.strip()

    result: dict[str, Any] = {
        "worked_solution": sections.get("worked solution", ""),
        "distractor_analysis": sections.get("distractor analysis", ""),
        "classification": sections.get("classification", ""),
        "difficulty_rating": sections.get("difficulty rating", ""),
        "diagram_descriptions": sections.get("diagram descriptions", ""),
    }

    has_content = all(v for k, v in result.items() if k != "diagram_descriptions")
    result["valid"] = has_content
    result["has_diagram_descriptions"] = bool(result["diagram_descriptions"])
    result["is_out_of_spec"] = "out_of_spec" in result["classification"].lower()

    return result


# ---------------------------------------------------------------------------
# Verification pass (GLM batch verification)
# ---------------------------------------------------------------------------

VERIFICATION_SYSTEM_PROMPT = """\
You are a QA reviewer for ESAT question enrichment data. You will be given \
a batch of questions with their enrichment data. For each question, verify:

1. **Solution correctness**: Does the worked solution arrive at the stated \
   correct answer? Check the math and logic.
2. **Option references**: Are all option letters (A, B, C, D, etc.) \
   referenced correctly? No missing, swapped, or mislabeled letters?
3. **Classification**: Is the classification sensible for the content?
4. **Difficulty**: Is the difficulty rating (1-10) reasonable?
5. **Formatting**: Any LaTeX errors, broken markdown, or formatting issues?

Output ONLY a JSON array — one object per question:
[
  {"question_id": "...", "verified": true, "issues": []},
  {"question_id": "...", "verified": false, "issues": ["...", "..."]}
]

Only report genuine issues. If enrichment is correct, verified=true, issues=[].
"""

VERIFICATION_BATCH_TEMPLATE = """\
Verify the following {count} questions:

{batch_content}
"""


def _extract_verification_context(question: dict[str, Any]) -> dict[str, Any]:
    """Extract essential fields from an enriched question for verification."""
    enrichment = question.get("enrichment", {})
    markdown = enrichment.get("markdown", "") or ""

    parsed = validate_enrichment(markdown)

    # Truncate worked solution to stay within context limits
    worked = parsed.get("worked_solution", "")
    if len(worked) > 1500:
        worked = worked[:1500] + "\n...[truncated]"

    classification = parsed.get("classification", "")
    if len(classification) > 300:
        classification = classification[:300] + "...[truncated]"

    difficulty = parsed.get("difficulty_rating", "")
    if len(difficulty) > 200:
        difficulty = difficulty[:200]

    return {
        "question_id": question.get("id", "unknown"),
        "question_text": question.get("question_text", "")[:800],
        "options": question.get("options", {}),
        "correct_answer": question.get("correct_answer", question.get("correct_answer_plain", "")),
        "worked_solution": worked,
        "classification": classification,
        "difficulty": difficulty,
    }


def _format_verification_batch(items: list[dict[str, Any]]) -> str:
    """Format a batch of verification items into a single prompt string."""
    parts: list[str] = []
    for i, item in enumerate(items):
        parts.append(f"--- Question {i + 1} ---")
        parts.append(f"ID: {item['question_id']}")
        parts.append(f"Question: {item['question_text']}")
        opts: dict = item.get("options", {})
        opt_lines = [f"  {k}: {v}" for k, v in opts.items()]
        parts.append("Options:\n" + "\n".join(opt_lines))
        parts.append(f"Correct Answer: {item['correct_answer']}")
        parts.append(f"Worked Solution:\n{item['worked_solution']}")
        parts.append(f"Classification:\n{item['classification']}")
        parts.append(f"Difficulty:\n{item['difficulty']}")
        parts.append("")
    return "\n".join(parts)


def verify_batch(
    client: openai.OpenAI,
    items: list[dict[str, Any]],
    model: str,
) -> list[dict[str, Any]]:
    """Send a batch of questions to GLM for verification.

    Returns a list of verification result dicts.
    """
    if not items:
        return []

    batch_content = _format_verification_batch(items)
    user_prompt = VERIFICATION_BATCH_TEMPLATE.format(
        count=len(items),
        batch_content=batch_content,
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": VERIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=MAX_TOKENS,
            messages=messages,
        )
        response_text = response.choices[0].message.content or ""

        # Extract JSON array from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            results = json.loads(json_match.group())
            return results
        else:
            logger.warning("Verification: no JSON array found in response")
            return [
                {"question_id": item["question_id"], "verified": True, "issues": ["Verification parse failure"]}
                for item in items
            ]

    except Exception as e:
        logger.error("Verification batch failed: %s", e)
        return [
            {"question_id": item["question_id"], "verified": True, "issues": [f"Verification error: {str(e)[:200]}"]}
            for item in items
        ]


def run_verification_pass(
    client: openai.OpenAI,
    enriched_questions: list[dict[str, Any]],
    model: str,
    batch_size: int = 100,
) -> dict[str, list[str]]:
    """Run verification on all enriched questions in batches.

    Returns a dict mapping question_id -> list of issues.
    Only questions with issues are included.
    """
    to_verify = [
        q for q in enriched_questions
        if q.get("enrichment", {}).get("status") in ("success", "out_of_spec")
        and q.get("enrichment", {}).get("markdown")
    ]

    if not to_verify:
        logger.info("No enriched questions to verify")
        return {}

    logger.info(
        "Starting verification pass: %d questions in batches of %d",
        len(to_verify), batch_size,
    )

    all_issues: dict[str, list[str]] = {}
    total_verified = 0

    for batch_start in range(0, len(to_verify), batch_size):
        batch = to_verify[batch_start:batch_start + batch_size]

        # Extract verification context
        contexts = [_extract_verification_context(q) for q in batch]

        # Check context size and reduce if needed
        total_chars = sum(len(json.dumps(c, ensure_ascii=False)) for c in contexts)
        max_context = 200_000  # Conservative limit
        if total_chars > max_context:
            usable = max(5, int(len(contexts) * max_context / total_chars))
            logger.warning(
                "Batch context too large (%d chars), reducing from %d to %d items",
                total_chars, len(contexts), usable,
            )
            batch = batch[:usable]
            contexts = contexts[:usable]

        logger.info(
            "Verifying batch %d-%d (%d questions)",
            batch_start + 1, batch_start + len(batch), len(batch),
        )

        results = verify_batch(client, contexts, model)

        for vr in results:
            qid = vr.get("question_id", "")
            issues = vr.get("issues", [])
            if not vr.get("verified", True) or issues:
                all_issues[qid] = issues
                logger.warning(
                    "Question %s: verification flagged %d issue(s): %s",
                    qid, len(issues), "; ".join(issues[:3]),
                )
            total_verified += 1

    logger.info(
        "Verification complete: %d verified, %d flagged with issues",
        total_verified, len(all_issues),
    )
    return all_issues


# ---------------------------------------------------------------------------
# Cost estimation (z.ai is free)
# ---------------------------------------------------------------------------


def estimate_cost(
    model: str,
    num_questions: int,
    avg_input_tokens: int = 18000,
    avg_output_tokens: int = 5000,
) -> float:
    """z.ai is free — always returns $0.00."""
    return 0.0


def calculate_actual_cost(
    model: str,
    results: list[EnrichmentResult],
) -> dict[str, float]:
    """z.ai is free — always returns $0.00."""
    return {"total": 0.0, "input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0}


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------


def count_total_questions(corpus_files: list[CorpusFile]) -> int:
    """Count total questions across all corpus files."""
    total = 0
    for cf in corpus_files:
        questions = load_questions_from_file(cf)
        total += len(questions)
    return total


def process_question(
    client: openai.OpenAI,
    question: dict[str, Any],
    corpus_file: CorpusFile,
    model: str,
    dry_run: bool = False,
    skip_diagrams: bool = True,
) -> EnrichmentResult:
    """Process a single question through the enrichment pipeline."""
    question_id = question.get("id", "unknown")
    has_diagram = question_has_diagram(question)

    # Skip diagram questions if requested (default for GLM — no vision support)
    if skip_diagrams and has_diagram:
        logger.info(
            "Question %s: SKIPPED (has diagram — GLM text-only endpoint cannot process images)",
            question_id,
        )
        if dry_run:
            logger.info("[DRY-RUN] Question %s (has_diagram=true → SKIPPED)", question_id)
        return EnrichmentResult(
            question_id=question_id,
            status="skipped",
            error="Skipped: has diagram (GLM text-only endpoint)",
        )

    # Build prompts
    taxonomy = resolve_taxonomy_context(corpus_file)
    system_prompt = build_system_prompt(corpus_file, taxonomy)
    user_prompt = build_user_prompt(question, corpus_file)

    if dry_run:
        logger.info("[DRY-RUN] Question %s (has_diagram=%s)", question_id, has_diagram)
        logger.info("[DRY-RUN] System prompt length: %d chars", len(system_prompt))
        logger.info("[DRY-RUN] User prompt length: %d chars", len(user_prompt))
        logger.info("[DRY-RUN] --- System prompt ---\n%s", system_prompt[:500])
        logger.info("[DRY-RUN] --- User prompt ---\n%s", user_prompt[:500])
        return EnrichmentResult(question_id=question_id, status="success")

    # Get image paths if diagram question
    image_paths = None
    if has_diagram:
        image_paths = question.get("diagram_images", []) or question.get("question_images", [])

    start_time = time.time()

    try:
        response_text, token_usage = call_glm_api(
            client=client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            image_paths=image_paths,
        )

        duration = time.time() - start_time

        # Validate output
        parsed = validate_enrichment(response_text)
        if not parsed["valid"]:
            logger.warning(
                "Question %s: output validation incomplete (missing sections)",
                question_id,
            )

        # Check for out-of-spec skip
        if parsed["is_out_of_spec"] and corpus_file.source_type == "nsaa_s2":
            logger.info("Question %s: marked OUT_OF_SPEC, skipping worked solution", question_id)
            return EnrichmentResult(
                question_id=question_id,
                status="out_of_spec",
                enrichment_markdown=response_text,
                input_tokens=token_usage["input_tokens"],
                output_tokens=token_usage["output_tokens"],
                duration_seconds=duration,
            )

        logger.info(
            "Question %s: enriched successfully (%d in, %d out tokens, %.1fs)",
            question_id,
            token_usage["input_tokens"],
            token_usage["output_tokens"],
            duration,
        )

        return EnrichmentResult(
            question_id=question_id,
            status="success",
            enrichment_markdown=response_text,
            input_tokens=token_usage["input_tokens"],
            output_tokens=token_usage["output_tokens"],
            duration_seconds=duration,
        )

    except Exception as e:
        duration = time.time() - start_time
        logger.error("Question %s: FAILED after %.1fs — %s", question_id, duration, e)
        return EnrichmentResult(
            question_id=question_id,
            status="failed",
            error=str(e),
            duration_seconds=duration,
        )


def process_corpus_file(
    client: openai.OpenAI,
    corpus_file: CorpusFile,
    model: str,
    output_dir: Path,
    limit: Optional[int] = None,
    dry_run: bool = False,
    skip_diagrams: bool = True,
    verify: bool = True,
    batch_size: int = 10,
    verify_model: Optional[str] = None,
    max_retries: int = 1,
) -> tuple[list[EnrichmentResult], dict[str, Any]]:
    """Process all questions in a single corpus file in batches.

    Questions are processed in batches of ``batch_size``. After each batch
    is enriched and verified, any verification failures trigger re-enrichment
    of the flagged questions. If re-verification still fails after
    ``max_retries`` attempts, the pipeline halts and exits with an error.

    Returns (results, verification_stats).
    """
    logger.info("Processing %s (%s)", corpus_file.path.name, corpus_file.source_type)

    questions = load_questions_from_file(corpus_file)
    if not questions:
        logger.warning("No questions found in %s", corpus_file.path)
        return [], {"total_verified": 0, "anomalies": 0, "pipeline_halted": False}

    if limit is not None:
        questions = questions[:limit]

    logger.info(
        "Processing %d question(s) from %s in batches of %d",
        len(questions), corpus_file.path.name, batch_size,
    )

    # Load original data for output
    with open(corpus_file.path, encoding="utf-8") as f:
        original_data = json.load(f)

    results: list[EnrichmentResult] = []
    enriched_questions: list[dict[str, Any]] = []
    verification_stats: dict[str, Any] = {"total_verified": 0, "anomalies": 0, "pipeline_halted": False}
    pipeline_halted = False
    halted_failures: list[tuple[str, list[str]]] = []
    v_model = verify_model or model

    # Process in batches: enrich -> verify -> fix if needed
    for batch_start in range(0, len(questions), batch_size):
        batch_questions = questions[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1

        logger.info(
            "=== Batch %d: questions %d-%d ===",
            batch_num, batch_start + 1, batch_start + len(batch_questions),
        )

        # --- Enrich all questions in batch ---
        batch_results: list[EnrichmentResult] = []
        batch_enriched: list[dict[str, Any]] = []

        for i, question in enumerate(batch_questions):
            global_idx = batch_start + i
            logger.info(
                "[%d/%d] Processing question %s",
                global_idx + 1, len(questions), question.get("id", "unknown"),
            )

            result = process_question(
                client=client,
                question=question,
                corpus_file=corpus_file,
                model=model,
                dry_run=dry_run,
                skip_diagrams=skip_diagrams,
            )
            batch_results.append(result)

            enriched = dict(question)
            enriched["enrichment"] = {
                "status": result.status,
                "model": model if not dry_run else "dry-run",
                "enriched_at": time.strftime("%Y-%m-%dT%H:%M:%S") if not dry_run else None,
                "markdown": result.enrichment_markdown if result.status in ("success", "out_of_spec") else None,
                "error": result.error if result.status == "failed" else None,
                "processor_id": model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }
            batch_enriched.append(enriched)

        # --- Verification pass for this batch ---
        if verify and not dry_run:
            verifiable: list[tuple[int, dict[str, Any]]] = [
                (idx, eq) for idx, eq in enumerate(batch_enriched)
                if eq.get("enrichment", {}).get("status") in ("success", "out_of_spec")
                and eq.get("enrichment", {}).get("markdown")
            ]

            if verifiable:
                contexts = [_extract_verification_context(eq) for _, eq in verifiable]

                # Reduce context if too large
                total_chars = sum(len(json.dumps(c, ensure_ascii=False)) for c in contexts)
                max_context = 200_000
                if total_chars > max_context:
                    usable = max(5, int(len(contexts) * max_context / total_chars))
                    logger.warning(
                        "Batch context too large (%d chars), reducing from %d to %d items",
                        total_chars, len(contexts), usable,
                    )
                    contexts = contexts[:usable]
                    verifiable = verifiable[:usable]

                logger.info("Verifying batch %d (%d questions)", batch_num, len(contexts))
                verifications = verify_batch(client, contexts, v_model)
                verification_stats["total_verified"] += len(verifiable)

                # Find flagged questions
                flagged_qids: set[str] = set()
                for vr in verifications:
                    qid = vr.get("question_id", "")
                    issues = vr.get("issues", [])
                    if not vr.get("verified", True) or issues:
                        flagged_qids.add(qid)
                        logger.warning(
                            "Question %s: verification flagged %d issue(s): %s",
                            qid, len(issues), "; ".join(issues[:3]),
                        )

                if flagged_qids:
                    # Set clean verification for non-flagged
                    for _, eq in verifiable:
                        qid = eq.get("id", "unknown")
                        if qid not in flagged_qids:
                            eq["enrichment"]["verification"] = {"verified": True, "issues": []}

                    # Re-enrich flagged questions
                    logger.info(
                        "Re-enriching %d flagged question(s) from batch %d",
                        len(flagged_qids), batch_num,
                    )
                    still_failing: list[tuple[str, list[str]]] = []

                    for orig_idx, eq in verifiable:
                        qid = eq.get("id", "unknown")
                        if qid not in flagged_qids:
                            continue

                        question = batch_questions[orig_idx]
                        retry_success = False
                        re_verifications: list[dict[str, Any]] = []

                        for attempt in range(max_retries):
                            logger.info(
                                "Re-enriching question %s (attempt %d/%d)",
                                qid, attempt + 1, max_retries,
                            )

                            re_result = process_question(
                                client=client,
                                question=question,
                                corpus_file=corpus_file,
                                model=model,
                                dry_run=False,
                                skip_diagrams=skip_diagrams,
                            )

                            if re_result.status not in ("success", "out_of_spec"):
                                logger.error(
                                    "Question %s: re-enrichment FAILED: %s",
                                    qid, re_result.error,
                                )
                                continue

                            # Update enriched data
                            eq["enrichment"]["markdown"] = re_result.enrichment_markdown
                            eq["enrichment"]["enriched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                            eq["enrichment"]["input_tokens"] = re_result.input_tokens
                            eq["enrichment"]["output_tokens"] = re_result.output_tokens

                            # Re-verify just this question
                            re_context = [_extract_verification_context(eq)]
                            logger.info("Re-verifying question %s", qid)
                            re_verifications = verify_batch(client, re_context, v_model)

                            if re_verifications:
                                rv = re_verifications[0]
                                rv_issues = rv.get("issues", [])

                                if not rv.get("verified", True) or rv_issues:
                                    logger.warning(
                                        "Question %s: STILL FAILING after retry %d: %s",
                                        qid, attempt + 1, "; ".join(rv_issues[:3]),
                                    )
                                else:
                                    logger.info(
                                        "Question %s: verification PASSED after re-enrichment",
                                        qid,
                                    )
                                    retry_success = True
                                    eq["enrichment"]["verification"] = {"verified": True, "issues": []}
                                    batch_results[orig_idx] = re_result
                                    break
                            else:
                                logger.info(
                                    "Question %s: re-verification inconclusive, treating as pass",
                                    qid,
                                )
                                retry_success = True
                                eq["enrichment"]["verification"] = {"verified": True, "issues": []}
                                batch_results[orig_idx] = re_result
                                break

                        if not retry_success:
                            last_issues: list[str] = []
                            if re_verifications:
                                last_issues = re_verifications[0].get("issues", [])
                            if not last_issues:
                                last_issues = ["Verification failed after retries"]

                            eq["enrichment"]["status"] = "verification_failed"
                            eq["enrichment"]["verification"] = {"verified": False, "issues": last_issues}
                            batch_results[orig_idx].status = "verification_failed"
                            batch_results[orig_idx].verification_verified = False
                            batch_results[orig_idx].verification_issues = last_issues
                            still_failing.append((qid, last_issues))
                            verification_stats["anomalies"] += 1

                    if still_failing:
                        pipeline_halted = True
                        halted_failures.extend(still_failing)
                        results.extend(batch_results)
                        enriched_questions.extend(batch_enriched)
                        break
                else:
                    # All clean
                    for _, eq in verifiable:
                        eq["enrichment"]["verification"] = {"verified": True, "issues": []}
            else:
                logger.info("No verifiable questions in batch %d", batch_num)
        else:
            # No verification -- set defaults
            for eq in batch_enriched:
                if eq.get("enrichment", {}).get("status") in ("success", "out_of_spec"):
                    eq["enrichment"]["verification"] = {"verified": True, "issues": []}

        results.extend(batch_results)
        enriched_questions.extend(batch_enriched)

    # --- Save output file ---
    output_file = None
    if not dry_run:
        output_file = output_dir / corpus_file.path.relative_to(CORPUS_DIR)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        output_data: dict[str, Any] = {}
        if isinstance(original_data, dict):
            output_data = dict(original_data)
            output_data["questions"] = enriched_questions
            output_data["enriched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            output_data["enrichment_model"] = model
            if pipeline_halted:
                output_data["pipeline_halted"] = True
                output_data["halted_reason"] = (
                    f"Verification failed for {len(halted_failures)} question(s) "
                    f"after {max_retries} retry(ies)"
                )
        else:
            output_data = enriched_questions

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info("Saved enriched output to %s", output_file)

    # --- Print halt summary and exit ---
    if pipeline_halted:
        verification_stats["pipeline_halted"] = True
        logger.error("PIPELINE HALTED: verification failure")
        print("\n" + "!" * 60)
        print("PIPELINE HALTED -- PERSISTENT VERIFICATION FAILURE")
        print("!" * 60)
        print(f"Failed question(s): {len(halted_failures)}")
        for qid, issues in halted_failures:
            print(f"  - {qid}:")
            for issue in issues[:5]:
                print(f"      - {issue}")
        print(f"Questions processed before halt: {len(enriched_questions)}")
        print(f"Retries attempted: {max_retries}")
        if output_file:
            print(f"Output saved to: {output_file}")
        print("!" * 60)
        sys.exit(1)

    return results, verification_stats


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------


def print_summary(results: list[EnrichmentResult], model: str, verification_stats: Optional[dict] = None) -> None:
    """Print a summary report of the enrichment run."""
    total = len(results)
    success = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "failed")
    out_of_spec = sum(1 for r in results if r.status == "out_of_spec")
    skipped = sum(1 for r in results if r.status == "skipped")

    total_input = sum(r.input_tokens for r in results)
    total_output = sum(r.output_tokens for r in results)
    total_duration = sum(r.duration_seconds for r in results)

    cost = calculate_actual_cost(model, results)

    print("\n" + "=" * 60)
    print("GLM ENRICHMENT PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  Model:            {model}")
    print(f"  Endpoint:         {ZAI_BASE_URL}")
    print(f"  Total questions:   {total}")
    print(f"  Successful:       {success}")
    print(f"  Out-of-spec:      {out_of_spec}")
    print(f"  Failed:           {failed}")
    print(f"  Skipped:          {skipped}")
    print("-" * 60)
    print(f"  Input tokens:     {total_input:,}")
    print(f"  Output tokens:    {total_output:,}")
    print(f"  Total duration:   {total_duration:.1f}s ({total_duration/60:.1f}min)")
    print("-" * 60)
    print(f"  Estimated cost:   ${cost['total']:.2f} (z.ai is free)")
    print("=" * 60)

    if verification_stats and verification_stats.get("total_verified", 0) > 0:
        print("\n--- Verification Summary ---")
        print(f"  Total verified:   {verification_stats['total_verified']}")
        print(f"  Anomalies:        {verification_stats['anomalies']}")
        if verification_stats["anomalies"] > 0:
            flagged = [r for r in results if not r.verification_verified]
            print(f"  Flagged questions:")
            for r in flagged:
                print(f"    - {r.question_id}: {'; '.join(r.verification_issues[:3])}")

    if failed > 0:
        print("\nFailed questions:")
        for r in results:
            if r.status == "failed":
                print(f"  - {r.question_id}: {r.error[:100]}")

    if out_of_spec > 0:
        print(f"\nOut-of-spec questions (NSAA S2): {out_of_spec}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ESAT Question Enrichment Pipeline via z.ai (GLM) API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single file
  python glm-enrichment.py --input corpus/json/esat/esat_specimen_physics.json

  # Process all NSAA S2 files
  python glm-enrichment.py --input corpus/json/nsaa_s2/

  # Dry run (no API calls)
  python glm-enrichment.py --dry-run --limit 3

  # Use a different model
  python glm-enrichment.py --model glm-5.2 --limit 10
        """,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=CORPUS_DIR,
        help="Path to a specific corpus JSON file or directory (default: entire corpus)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"z.ai model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process N questions per file (for trial/testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompts without calling API",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Where to save results (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="z.ai API key (or set ZAI_API_KEY env var)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=ZAI_BASE_URL,
        help=f"z.ai API base URL (default: {ZAI_BASE_URL})",
    )
    parser.add_argument(
        "--skip-diagrams",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip questions with diagrams (default: True, since GLM text-only cannot handle images)",
    )
    parser.add_argument(
        "--verify",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run verification pass after enrichment (default: True)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for processing and verification pass (default: 10)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Max re-enrichment attempts on verification failure (default: 1)",
    )
    parser.add_argument(
        "--verify-model",
        type=str,
        default=None,
        help="Model for verification pass (default: same as --model)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # API key
    api_key = args.api_key or os.environ.get("ZAI_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: z.ai API key required. Set ZAI_API_KEY environment variable", file=sys.stderr)
        print("       or pass --api-key argument.", file=sys.stderr)
        sys.exit(1)

    # Load corpus files
    corpus_files = load_corpus_files(args.input)
    if not corpus_files:
        logger.error("No corpus files found")
        sys.exit(1)

    if args.skip_diagrams:
        logger.info("Diagram questions will be SKIPPED (--skip-diagrams is on)")
    else:
        logger.info("Diagram questions will be processed (--skip-diagrams is off)")

    # Count total questions for info
    if not args.dry_run:
        total_qs = 0
        for cf in corpus_files:
            qs = load_questions_from_file(cf)
            total_qs += len(qs) if args.limit is None else min(len(qs), args.limit)

        print(f"\nProcessing {total_qs} question(s) with {args.model} (z.ai — free)")
        print(f"  Output directory: {args.output_dir}")
        print()

    # Create client
    client = openai.OpenAI(api_key=api_key, base_url=args.base_url) if api_key else None

    # Process files
    all_results: list[EnrichmentResult] = []
    all_verification_stats: dict[str, Any] = {"total_verified": 0, "anomalies": 0}
    for corpus_file in corpus_files:
        results, v_stats = process_corpus_file(
            client=client,
            corpus_file=corpus_file,
            model=args.model,
            output_dir=args.output_dir,
            limit=args.limit,
            dry_run=args.dry_run,
            skip_diagrams=args.skip_diagrams,
            verify=args.verify,
            batch_size=args.batch_size,
            verify_model=args.verify_model,
            max_retries=args.max_retries,
        )
        all_results.extend(results)
        all_verification_stats["total_verified"] += v_stats.get("total_verified", 0)
        all_verification_stats["anomalies"] += v_stats.get("anomalies", 0)
        if v_stats.get("pipeline_halted", False):
            logger.error("Pipeline halted during processing of %s", corpus_file.path.name)
            break

    # Print summary
    if all_results:
        print_summary(all_results, args.model, all_verification_stats)

    logger.info("Done.")


if __name__ == "__main__":
    main()
