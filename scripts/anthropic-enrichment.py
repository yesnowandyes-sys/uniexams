#!/usr/bin/env python3
"""
Anthropic API Enrichment Pipeline for ESAT Questions.

Reads questions from the ESAT corpus, sends each through the Anthropic
Messages API for enrichment (worked solutions, distractor analysis,
classification, difficulty rating, diagram descriptions), and saves
structured results.

Usage:
    python anthropic-enrichment.py --input corpus/json/esat/esat_specimen_physics.json
    python anthropic-enrichment.py --input corpus/json/ --limit 5
    python anthropic-enrichment.py --dry-run --limit 3
    python anthropic-enrichment.py --model claude-sonnet-4-20250514 --limit 10

Environment:
    ANTHROPIC_API_KEY  — Required. Anthropic API key.
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

import anthropic
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
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "enriched-output"

# Anthropic model pricing (USD per million tokens)
# Source: https://docs.anthropic.com/en/docs/about-claude/models
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.30},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.50},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.30},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.0, "cache_write": 1.0, "cache_read": 0.08},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.50},
}

DEFAULT_MODEL = "claude-sonnet-4-20250514"

MAX_RETRIES = 5
RETRY_BASE_DELAY = 2.0  # seconds, doubled on each retry

ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"

# ---------------------------------------------------------------------------
# System prompt (static — cached across calls)
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
# User prompt template (dynamic — unique per question)
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

# Diagram variant of the user prompt (for diagram questions)
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
# Out-of-spec topics for NSAA S2 filtering
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
logger = logging.getLogger("anthropic-enrichment")

# ---------------------------------------------------------------------------
# Data classes
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
    diagram_vision_description: str = ""


@dataclass
class CorpusFile:
    """A single corpus JSON file and its metadata."""

    path: Path
    source_type: str  # esat, engaa, nsaa, nsaa_s2, tmua
    section: Optional[str] = None
    subject: Optional[str] = None
    module: Optional[str] = None


# ---------------------------------------------------------------------------
# Corpus loading
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
        # tmua files: 2022_p1.json → section P1
        name = path.stem
        parts2 = name.split("_", 1)
        if len(parts2) == 2:
            section = parts2[1].upper()
    elif source_type == "nsaa_s2":
        section = "S2"
        # nsaa_2020_s2_physics.json → subject=physics
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
    # Try relative to CWD
    cwd_candidate = Path.cwd() / input_path
    if cwd_candidate.exists():
        return cwd_candidate.resolve()
    # Try relative to CORPUS_DIR
    corpus_candidate = CORPUS_DIR / input_path
    if corpus_candidate.exists():
        return corpus_candidate
    # Return resolved path (may not exist)
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
# Prompt building
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
    # Handle correct_answer_plain for ESAT files that use it
    if not correct_answer:
        correct_answer = question.get("correct_answer_plain", "")

    options_list = format_options(options)

    # Check for diagram images
    diagram_images = question.get("diagram_images", []) or question.get("question_images", [])

    if diagram_images:
        # Build diagram content placeholder
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
    """
    Resolve which ESAT taxonomy modules are relevant for this corpus file.
    Returns a placeholder string noting the relevant modules.

    In a full implementation, this would load the actual ESAT taxonomy JSON
    and format the relevant modules. For now, we include module info so the
    model can self-classify.
    """
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
# API calling
# ---------------------------------------------------------------------------


def call_anthropic_api(
    client: anthropic.Anthropic,
    system_prompt: str,
    user_prompt: str,
    model: str,
    image_paths: Optional[list[str]] = None,
) -> tuple[str, dict[str, int]]:
    """
    Call the Anthropic Messages API with retry logic.

    Returns (response_text, token_usage_dict).
    Raises RuntimeError after exhausting retries.
    """
    messages: list[dict[str, Any]] = []

    # Build content blocks
    content_blocks: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]

    # Attach diagram images if present
    if image_paths:
        for img_path in image_paths:
            abs_path = img_path if os.path.isabs(img_path) else str(CORPUS_DIR.parent / "images" / img_path)
            if os.path.exists(abs_path):
                with open(abs_path, "rb") as img_f:
                    img_data = base64.standard_b64encode(img_f.read()).decode("utf-8")
                # Detect media type
                ext = Path(abs_path).suffix.lower()
                media_type = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".webp": "image/webp",
                    ".gif": "image/gif",
                }.get(ext, "image/png")

                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": img_data,
                    },
                })
            else:
                logger.warning("Diagram image not found: %s", abs_path)

    messages.append({"role": "user", "content": content_blocks})

    last_exception: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": 4096,
                "system": [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": messages,
            }

            response = client.messages.create(**kwargs)

            # Extract text from response
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text += block.text

            token_usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            }

            return response_text, token_usage

        except anthropic.RateLimitError as e:
            last_exception = e
            delay = RETRY_BASE_DELAY * (2 ** attempt) + 1
            logger.warning(
                "Rate limit hit (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, delay, e,
            )
            time.sleep(delay)

        except anthropic.APIConnectionError as e:
            last_exception = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Connection error (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, delay, e,
            )
            time.sleep(delay)

        except anthropic.APIStatusError as e:
            # Don't retry on 4xx errors (except 429 which is RateLimitError)
            if 400 <= e.status_code < 500 and e.status_code != 429:
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
# Output parsing / validation
# ---------------------------------------------------------------------------


def validate_enrichment(text: str) -> dict[str, Any]:
    """
    Parse the enrichment markdown into structured sections.

    Returns a dict with keys: worked_solution, distractor_analysis,
    classification, difficulty_rating, diagram_descriptions.
    """
    sections: dict[str, str] = {}

    # Split by ## headers
    pattern = r"^##\s+(.+)$"
    parts = re.split(pattern, text, flags=re.MULTILINE)

    # parts[0] is any text before first ##, then alternating: header, content
    current_section = None
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # This is a header
            current_section = part.strip().lower()
        else:
            # This is content
            if current_section:
                sections[current_section] = part.strip()

    # Map section names to canonical keys
    result: dict[str, Any] = {
        "worked_solution": sections.get("worked solution", ""),
        "distractor_analysis": sections.get("distractor analysis", ""),
        "classification": sections.get("classification", ""),
        "difficulty_rating": sections.get("difficulty rating", ""),
        "diagram_descriptions": sections.get("diagram descriptions", ""),
    }

    # Validate minimum content
    has_content = all(v for k, v in result.items() if k != "diagram_descriptions")
    result["valid"] = has_content
    result["has_diagram_descriptions"] = bool(result["diagram_descriptions"])
    result["is_out_of_spec"] = "out_of_spec" in result["classification"].lower()

    return result


# ---------------------------------------------------------------------------
# GLM vision + verification helpers
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


VISION_DESCRIPTION_PROMPT = """\
Describe this diagram in detail for use in question verification. \
Identify all visible elements:
- Axes (labels, units, ranges, scales)
- Curves, lines, and their shapes/intersections
- Labels and annotations
- Points, markers, or regions of interest
- Any numerical values shown
- Physical components (resistors, masses, springs, circuits, etc.)
- Spatial relationships and geometry

Provide a clear, complete description that would allow someone who cannot \
see the image to understand exactly what the diagram shows.
"""


def get_diagram_vision_description(
    zai_client: openai.OpenAI,
    image_paths: list[str],
    vision_model: str,
) -> Optional[str]:
    """Use GLM-4.7 (or specified vision model) to describe a diagram image.

    Returns a plain-text description, or None on failure.
    """
    # Encode images
    data_uris: list[str] = []
    for img_path in image_paths:
        abs_path = img_path if os.path.isabs(img_path) else str(CORPUS_DIR.parent / "images" / img_path)
        data_uri = _encode_image_as_data_uri(abs_path)
        if data_uri:
            data_uris.append(data_uri)

    if not data_uris:
        logger.warning("No images could be loaded for vision description")
        return None

    # Build multimodal content
    content_blocks: list[dict[str, Any]] = [
        {"type": "text", "text": VISION_DESCRIPTION_PROMPT},
    ]
    for uri in data_uris:
        content_blocks.append({
            "type": "image_url",
            "image_url": {"url": uri, "detail": "auto"},
        })

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": content_blocks},
    ]

    try:
        response = zai_client.chat.completions.create(
            model=vision_model,
            max_tokens=4096,
            messages=messages,
        )
        description = response.choices[0].message.content or ""
        logger.info("Vision description generated (%d chars) with %s", len(description), vision_model)
        return description
    except Exception as e:
        logger.error("Vision description failed with %s: %s", vision_model, e)
        return None


VERIFICATION_SYSTEM_PROMPT = """\
You are a QA reviewer for ESAT question enrichment data. You will be given \
a question with its enrichment markdown, the correct answer, and a \
description of any diagram. Verify:

1. **Solution correctness**: Does the worked solution arrive at the stated \
   correct answer? Check the math and logic step by step.
2. **Diagram interpretation**: If a diagram description is provided, does \
   the solution correctly interpret what the diagram shows?
3. **Option references**: Are all option letters (A, B, C, D, etc.) \
   referenced correctly? No missing, swapped, or mislabeled letters?
4. **Classification**: Is the classification sensible for the content?
5. **Difficulty**: Is the difficulty rating (1-10) reasonable?
6. **Formatting**: Any LaTeX errors, broken markdown, or formatting issues?

Output ONLY a JSON object (not an array — just one question):

{"question_id": "...", "verified": true/false, "issues": ["...", "..."]}

Only report genuine issues. If enrichment is correct, verified=true, issues=[].
"""

VERIFICATION_USER_TEMPLATE = """\
Verify this question's enrichment:

**Question ID:** {question_id}

**Question Text:**
{question_text}

**Options:**
{options_list}

**Correct Answer:** {correct_answer}

**Diagram Description (from vision model):**
{diagram_description}

**Enrichment Markdown:**
{enrichment_markdown}
"""


def verify_diagram_with_glm(
    zai_client: openai.OpenAI,
    question: dict[str, Any],
    enrichment_markdown: str,
    diagram_description: Optional[str],
    verify_model: str = "glm-5.2",
) -> Optional[dict[str, Any]]:
    """Use GLM-5.2 to verify a single enriched question.

    Returns {"verified": bool, "issues": [...]} or None on failure.
    """
    question_id = question.get("id", "unknown")
    question_text = question.get("question_text", "")
    options = question.get("options", {})
    correct_answer = question.get("correct_answer", question.get("correct_answer_plain", ""))

    # Truncate enrichment markdown if very long
    markdown = enrichment_markdown
    if len(markdown) > 8000:
        markdown = markdown[:8000] + "\n...[truncated]"

    options_list = format_options(options)
    diag_desc = diagram_description or "(No diagram description available)"

    user_prompt = VERIFICATION_USER_TEMPLATE.format(
        question_id=question_id,
        question_text=question_text,
        options_list=options_list,
        correct_answer=correct_answer,
        diagram_description=diag_desc,
        enrichment_markdown=markdown,
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": VERIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = zai_client.chat.completions.create(
            model=verify_model,
            max_tokens=4096,
            messages=messages,
        )
        response_text = response.choices[0].message.content or ""

        # Extract JSON object from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            logger.warning("Verification for %s: no JSON found in response", question_id)
            return None

    except Exception as e:
        logger.error("Verification failed for %s: %s", question_id, e)
        return None


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def estimate_cost(
    model: str,
    num_questions: int,
    avg_input_tokens: int = 18000,
    avg_output_tokens: int = 5000,
) -> float:
    """Estimate total cost for processing N questions."""
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        logger.warning("No pricing data for model %s, cannot estimate cost", model)
        return 0.0

    # Assume ~80% of input is cached after first call
    total_input = num_questions * avg_input_tokens
    total_output = num_questions * avg_output_tokens
    uncached_input = num_questions * avg_input_tokens * 0.2  # 20% dynamic
    cached_input = num_questions * avg_input_tokens * 0.8  # 80% cached
    cache_write = avg_input_tokens  # first call cache write

    cost = (
        cache_write * pricing["cache_write"] / 1_000_000
        + (cached_input - cache_write) * pricing["cache_read"] / 1_000_000
        + uncached_input * pricing["input"] / 1_000_000
        + total_output * pricing["output"] / 1_000_000
    )
    return cost


def calculate_actual_cost(
    model: str,
    results: list[EnrichmentResult],
) -> dict[str, float]:
    """Calculate actual cost from token usage across all results."""
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return {"total": 0.0, "input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0}

    total_input = sum(r.input_tokens for r in results)
    total_output = sum(r.output_tokens for r in results)
    total_cache_read = sum(r.cache_read_tokens for r in results)
    total_cache_write = sum(r.cache_creation_tokens for r in results)

    # Regular input tokens = total_input - cache_read - cache_write
    regular_input = total_input - total_cache_read - total_cache_write

    cost = {
        "input": regular_input * pricing["input"] / 1_000_000,
        "output": total_output * pricing["output"] / 1_000_000,
        "cache_read": total_cache_read * pricing["cache_read"] / 1_000_000,
        "cache_write": total_cache_write * pricing["cache_write"] / 1_000_000,
    }
    cost["total"] = sum(cost.values())

    return cost


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
    client: anthropic.Anthropic,
    question: dict[str, Any],
    corpus_file: CorpusFile,
    model: str,
    dry_run: bool = False,
    skip_diagrams: bool = False,
    zai_client: Optional[openai.OpenAI] = None,
    verify: bool = True,
    vision_model: str = "glm-4.7",
) -> EnrichmentResult:
    """Process a single question through the enrichment pipeline."""
    question_id = question.get("id", "unknown")
    has_diagram = question_has_diagram(question)

    # Skip diagram questions if requested
    if skip_diagrams and has_diagram:
        logger.info(
            "Question %s: SKIPPED (has diagram --skip-diagrams is on)",
            question_id,
        )
        if dry_run:
            logger.info("[DRY-RUN] Question %s (has_diagram=true → SKIPPED)", question_id)
        return EnrichmentResult(
            question_id=question_id,
            status="skipped",
            error="Skipped: has diagram (--skip-diagrams)",
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
        response_text, token_usage = call_anthropic_api(
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
                cache_read_tokens=token_usage["cache_read_tokens"],
                cache_creation_tokens=token_usage["cache_creation_tokens"],
                duration_seconds=duration,
            )

        # --- Stage 1: GLM vision description (for diagram questions) ---
        diagram_vision_description: Optional[str] = None
        if verify and zai_client and has_diagram and image_paths:
            diagram_vision_description = get_diagram_vision_description(
                zai_client, image_paths, vision_model,
            )

        # --- Stage 2: GLM-5.2 verification ---
        verification_result: Optional[dict[str, Any]] = None
        if verify and zai_client:
            verification_result = verify_diagram_with_glm(
                zai_client,
                question,
                response_text,
                diagram_vision_description,
            )
            if verification_result and not verification_result.get("verified", True):
                logger.warning(
                    "Question %s: verification flagged %d issue(s): %s",
                    question_id,
                    len(verification_result.get("issues", [])),
                    "; ".join(verification_result.get("issues", [])[:3]),
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
            cache_read_tokens=token_usage["cache_read_tokens"],
            cache_creation_tokens=token_usage["cache_creation_tokens"],
            duration_seconds=duration,
            verification_verified=(verification_result or {}).get("verified", True),
            verification_issues=(verification_result or {}).get("issues", []),
            diagram_vision_description=diagram_vision_description or "",
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
    client: anthropic.Anthropic,
    corpus_file: CorpusFile,
    model: str,
    output_dir: Path,
    limit: Optional[int] = None,
    dry_run: bool = False,
    skip_diagrams: bool = False,
    diagrams_only: bool = False,
    zai_client: Optional[openai.OpenAI] = None,
    verify: bool = True,
    vision_model: str = "glm-4.7",
    max_retries: int = 1,
) -> list[EnrichmentResult]:
    """Process all questions in a single corpus file.

    After each question is enriched and verified (GLM-4.7 description +
    GLM-5.2 verification), if verification flags issues, the question is
    re-enriched via Opus and both verification stages are re-run. If still
    failing after max_retries, the pipeline halts and exits with an error.
    """
    logger.info("Processing %s (%s)", corpus_file.path.name, corpus_file.source_type)

    questions = load_questions_from_file(corpus_file)
    if not questions:
        logger.warning("No questions found in %s", corpus_file.path)
        return []

    # Filter by diagram status BEFORE applying limit
    if diagrams_only:
        before_count = len(questions)
        questions = [q for q in questions if question_has_diagram(q)]
        logger.info(
            "--diagrams-only filter: %d/%d questions have diagrams",
            len(questions), before_count,
        )
    elif skip_diagrams:
        before_count = len(questions)
        questions = [q for q in questions if not question_has_diagram(q)]
        logger.info(
            "--skip-diagrams filter: %d/%d questions without diagrams",
            len(questions), before_count,
        )

    if limit is not None:
        questions = questions[:limit]

    logger.info("Processing %d question(s) from %s", len(questions), corpus_file.path.name)

    results: list[EnrichmentResult] = []
    enriched_questions: list[dict[str, Any]] = []

    # Load original file for metadata
    with open(corpus_file.path, encoding="utf-8") as f:
        original_data = json.load(f)

    pipeline_halted = False
    halted_failures: list[tuple[str, list[str]]] = []

    for i, question in enumerate(questions):
        logger.info(
            "[%d/%d] Processing question %s",
            i + 1, len(questions), question.get("id", "unknown"),
        )

        result = process_question(
            client=client,
            question=question,
            corpus_file=corpus_file,
            model=model,
            dry_run=dry_run,
            skip_diagrams=False,  # already filtered at corpus level
            zai_client=zai_client,
            verify=verify,
            vision_model=vision_model,
        )

        # --- Auto-fix: re-enrich on verification failure ---
        question_id = question.get("id", "unknown")
        if (
            verify
            and not dry_run
            and result.status in ("success", "out_of_spec")
            and not result.verification_verified
        ):
            logger.warning(
                "Question %s: verification flagged %d issue(s): %s",
                question_id,
                len(result.verification_issues),
                "; ".join(result.verification_issues[:3]),
            )

            for attempt in range(max_retries):
                logger.info(
                    "Question %s: re-enriching (attempt %d/%d)",
                    question_id, attempt + 1, max_retries,
                )

                result = process_question(
                    client=client,
                    question=question,
                    corpus_file=corpus_file,
                    model=model,
                    dry_run=False,
                    skip_diagrams=False,
                    zai_client=zai_client,
                    verify=verify,
                    vision_model=vision_model,
                )

                if result.verification_verified:
                    logger.info(
                        "Question %s: verification PASSED after re-enrichment",
                        question_id,
                    )
                    break

                logger.warning(
                    "Question %s: STILL FAILING after retry %d: %s",
                    question_id, attempt + 1,
                    "; ".join(result.verification_issues[:3]),
                )

            if not result.verification_verified:
                # Mark as verification_failed
                result.status = "verification_failed"
                halted_failures.append((question_id, result.verification_issues))

        results.append(result)

        # Merge enrichment into question data
        enriched = dict(question)
        enrichment_data: dict[str, Any] = {
            "status": result.status,
            "model": model if not dry_run else "dry-run",
            "enriched_at": time.strftime("%Y-%m-%dT%H:%M:%S") if not dry_run else None,
            "markdown": result.enrichment_markdown if result.status in ("success", "out_of_spec", "verification_failed") else None,
            "error": result.error if result.status == "failed" else None,
            "processor_id": model,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }
        if result.diagram_vision_description:
            enrichment_data["diagram_vision_description"] = result.diagram_vision_description
        if result.status in ("success", "out_of_spec", "verification_failed") and verify:
            enrichment_data["verification"] = {
                "verified": result.verification_verified,
                "issues": result.verification_issues,
            }
        enriched["enrichment"] = enrichment_data
        enriched_questions.append(enriched)

        # If verification failed after retries, save progress and halt
        if result.status == "verification_failed":
            pipeline_halted = True
            break

    # Save output file
    if not dry_run:
        output_file = output_dir / corpus_file.path.relative_to(CORPUS_DIR)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Preserve original structure
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
    else:
        output_file = None

    # Print halt summary and exit
    if pipeline_halted:
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

    return results


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
    total_cache_read = sum(r.cache_read_tokens for r in results)
    total_cache_write = sum(r.cache_creation_tokens for r in results)
    total_duration = sum(r.duration_seconds for r in results)

    cost = calculate_actual_cost(model, results)

    print("\n" + "=" * 60)
    print("ENRICHMENT PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  Model:            {model}")
    print(f"  Total questions:   {total}")
    print(f"  Successful:       {success}")
    print(f"  Out-of-spec:      {out_of_spec}")
    print(f"  Failed:           {failed}")
    print(f"  Skipped:          {skipped}")
    print("-" * 60)
    print(f"  Input tokens:     {total_input:,}")
    print(f"  Output tokens:    {total_output:,}")
    print(f"  Cache read:       {total_cache_read:,}")
    print(f"  Cache write:      {total_cache_write:,}")
    print(f"  Total duration:   {total_duration:.1f}s ({total_duration/60:.1f}min)")
    print("-" * 60)
    print(f"  Estimated cost:   ${cost['total']:.4f}")
    print(f"    Input:          ${cost['input']:.4f}")
    print(f"    Output:         ${cost['output']:.4f}")
    print(f"    Cache read:     ${cost['cache_read']:.4f}")
    print(f"    Cache write:    ${cost['cache_write']:.4f}")
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
        description="ESAT Question Enrichment Pipeline via Anthropic API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single file
  python anthropic-enrichment.py --input corpus/json/esat/esat_specimen_physics.json

  # Process all NSAA S2 files
  python anthropic-enrichment.py --input corpus/json/nsaa_s2/

  # Dry run (no API calls)
  python anthropic-enrichment.py --dry-run --limit 3

  # Use Opus for diagram questions
  python anthropic-enrichment.py --model claude-opus-4-20250514 --limit 5
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
        help=f"Anthropic model name (default: {DEFAULT_MODEL})",
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
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "--diagrams-only",
        action="store_true",
        help="Only process questions that have diagrams (for Opus vision pipeline)",
    )
    parser.add_argument(
        "--skip-diagrams",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Skip questions with diagrams (default: False)",
    )
    parser.add_argument(
        "--verify",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run GLM vision + verification stages after enrichment (default: True)",
    )
    parser.add_argument(
        "--vision-model",
        type=str,
        default="glm-4.7",
        help="GLM vision model for diagram description (default: glm-4.7)",
    )
    parser.add_argument(
        "--verify-model",
        type=str,
        default="glm-5.2",
        help="GLM model for verification pass (default: glm-5.2)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Max re-enrichment attempts on verification failure (default: 1)",
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
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: Anthropic API key required. Set ANTHROPIC_API_KEY environment variable", file=sys.stderr)
        print("       or pass --api-key argument.", file=sys.stderr)
        sys.exit(1)

    # Load corpus files
    corpus_files = load_corpus_files(args.input)
    if not corpus_files:
        logger.error("No corpus files found")
        sys.exit(1)

    if args.diagrams_only:
        logger.info("Filtering to DIAGRAM-ONLY questions (--diagrams-only)")
    if args.skip_diagrams:
        logger.info("Diagram questions will be SKIPPED (--skip-diagrams)")

    # Count total questions for cost estimate
    if not args.dry_run:
        total_qs = 0
        for cf in corpus_files:
            qs = load_questions_from_file(cf)
            total_qs += len(qs) if args.limit is None else min(len(qs), args.limit)

        est_cost = estimate_cost(args.model, total_qs)
        pricing = MODEL_PRICING.get(args.model)
        print(f"\nEstimated cost for {total_qs} questions with {args.model}:")
        if pricing:
            print(f"  Input:  ${pricing['input']}/MTok")
            print(f"  Output: ${pricing['output']}/MTok")
            if pricing.get("cache_read"):
                print(f"  Cache read:  ${pricing['cache_read']}/MTok (90%% discount)")
            if pricing.get("cache_write"):
                print(f"  Cache write: ${pricing['cache_write']}/MTok (25%% premium)")
        print(f"  Estimated total: ~${est_cost:.4f}")
        print()

    # Create Anthropic client
    client = anthropic.Anthropic(api_key=api_key) if api_key else None

    # Create z.ai client for verification (if enabled)
    zai_client: Optional[openai.OpenAI] = None
    if args.verify and not args.dry_run:
        zai_api_key = os.environ.get("ZAI_API_KEY")
        if zai_api_key:
            zai_client = openai.OpenAI(api_key=zai_api_key, base_url=ZAI_BASE_URL)
            logger.info("z.ai client created for verification (vision=%s, verify=%s)", args.vision_model, args.verify_model)
        else:
            logger.warning("ZAI_API_KEY not set — verification will be skipped")
            args.verify = False

    # Verification stats accumulator
    all_verification_stats: dict[str, Any] = {"total_verified": 0, "anomalies": 0}

    # Process files
    all_results: list[EnrichmentResult] = []
    for corpus_file in corpus_files:
        results = process_corpus_file(
            client=client,
            corpus_file=corpus_file,
            model=args.model,
            output_dir=args.output_dir,
            limit=args.limit,
            dry_run=args.dry_run,
            skip_diagrams=args.skip_diagrams,
            diagrams_only=args.diagrams_only,
            zai_client=zai_client,
            verify=args.verify,
            vision_model=args.vision_model,
            max_retries=args.max_retries,
        )
        all_results.extend(results)

    # Aggregate verification stats
    if args.verify and not args.dry_run:
        verified_results = [r for r in all_results if r.status in ("success", "out_of_spec")]
        all_verification_stats["total_verified"] = len(verified_results)
        all_verification_stats["anomalies"] = sum(1 for r in verified_results if not r.verification_verified)

    # Print summary
    if all_results:
        print_summary(all_results, args.model, all_verification_stats)

    logger.info("Done.")


if __name__ == "__main__":
    main()
