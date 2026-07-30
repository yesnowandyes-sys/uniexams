#!/usr/bin/env python3
"""
Batch Opus Enrichment Pipeline for all ESAT corpus questions.

Processes every question under corpus/json/ through Claude Opus 4.8 and
produces enrichment data in the format the database ingests:

    {
      "status": "success",
      "model": "claude-opus-4-8",
      "enriched_at": "2026-07-10T12:00:00",
      "markdown": "<full worked solution + analysis>",
      "difficulty_rating": 4,                      # 1-10
      "difficulty_category": "Easy",               # Easy|Medium|Hard|Very Hard
      "topic_classification": {                    # from esat_taxonomy.json
        "module_code": "M1",
        "module_name": "Mathematics 1",
        "topic_code": "M1.3",
        "topic_name": "Number",
        "content_code": "M1.3",
        "is_out_of_spec": false
      },
      "ocr_corrections": [],                       # suggested OCR fixes
      "verification": { "verified": true, "issues": [] },
      "error": null,
      "processor_id": "claude-opus-4-8",
      "input_tokens": 184,
      "output_tokens": 1848,
      "attempts": 1
    }

Key features:

  - **Resume from failures** — per-question state manifest at
    enriched-output/opus-batch/_state.json. Re-running the script skips
    questions already marked success and only retries pending/failed.
  - **Real taxonomy loading** — loads esat_taxonomy.json once and embeds
    the relevant module's full topic list in each system prompt.
  - **Rate limit handling** — exponential backoff + jitter, plus
    per-request timeout and MAX_RETRIES.
  - **Concurrency** — N parallel workers (default 3), tunable via
    --concurrency. Set to 1 for strict serial.
  - **Cost guardrail** — stops when accumulated cost exceeds --max-cost-usd.
  - **Database-ready output** — writes one file per corpus file under
    enriched-output/opus-batch/<source>/<filename>.json, mirroring the
    opus-trial format. Existing import-corpus.ts already ingests this.

Usage:

    # Dry-run (no API calls)
    python opus-batch-enrichment.py --dry-run --limit 5

    # Tiny live test on one file
    python opus-batch-enrichment.py --input corpus/json/tmua/specimen_p1.json --limit 2

    # Full run (resume-aware)
    python opus-batch-enrichment.py

    # Force re-enrich everything
    python opus-batch-enrichment.py --reset

Environment:
    ANTHROPIC_API_KEY  — Required for live calls (z.ai or Anthropic).
    ANTHROPIC_BASE_URL — Optional (defaults to Anthropic, override for z.ai gateway).
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

import anthropic

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPT_DIR.parent
CORPUS_DIR = SHARED_DIR / "corpus" / "json"
TAXONOMY_PATH = SHARED_DIR / "esat_taxonomy.json"
IMAGES_DIR = SHARED_DIR / "corpus" / "images"
DEFAULT_OUTPUT_DIR = SHARED_DIR / "enriched-output" / "opus-batch"
STATE_PATH = DEFAULT_OUTPUT_DIR / "_state.json"
RUN_LOG_PATH = DEFAULT_OUTPUT_DIR / "_run_log.jsonl"

DEFAULT_MODEL = "claude-opus-4-8"

# Opus 4.x list pricing (USD per million tokens). Used for the cost guardrail
# and the per-run summary. If the actual gateway charges differently the only
# effect is an inaccurate cost estimate — enrichment proceeds regardless.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-8": {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.50},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.50},
}

MAX_RETRIES = 6
RETRY_BASE_DELAY = 3.0
REQUEST_MAX_TOKENS = 4096
REQUEST_TIMEOUT_SECONDS = 180
MAX_IMAGES_PER_QUESTION = 4  # hard cap; extra diagrams beyond this are noted but not sent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("opus-batch")

# Suppress noisy httpx logs unless debugging
logging.getLogger("httpx").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CorpusFile:
    """A single corpus JSON file."""

    path: Path
    source_type: str  # esat | engaa | nsaa | nsaa_s2 | tmua
    section: Optional[str] = None
    subject: Optional[str] = None
    module: Optional[str] = None


@dataclass
class EnrichmentResult:
    """Result of enriching a single question."""

    question_id: str
    source_file: str  # relative path for grouping
    status: str  # success | failed | out_of_spec | skipped
    enrichment_markdown: str = ""
    difficulty_rating: Optional[int] = None
    difficulty_category: Optional[str] = None
    topic_classification: dict[str, Any] = field(default_factory=dict)
    ocr_corrections: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    duration_seconds: float = 0.0
    attempts: int = 0


# ---------------------------------------------------------------------------
# Taxonomy loading
# ---------------------------------------------------------------------------


def load_taxonomy(path: Path = TAXONOMY_PATH) -> dict[str, Any]:
    """Load esat_taxonomy.json. Returns empty dict if missing."""
    if not path.exists():
        logger.warning("Taxonomy not found at %s — proceeding without it", path)
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def render_taxonomy_for_module(
    taxonomy: dict[str, Any],
    source_type: str,
    module: Optional[str] = None,
    subject: Optional[str] = None,
    section: Optional[str] = None,
) -> str:
    """Render the relevant module(s) of the ESAT taxonomy as text for the prompt.

    Mirrors the corpus-source → taxonomy-module mapping used in the existing
    anthropic-enrichment.py, but actually serialises the topic list instead of
    a placeholder note.
    """
    if not taxonomy:
        return "(Taxonomy unavailable — classify based on standard ESAT subject content.)"

    modules = taxonomy.get("modules", [])
    by_code: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for m in modules:
        by_code[m.get("code", "").upper()] = m
        by_name[m.get("name", "").lower()] = m

    def find(codes: Iterable[str], names: Iterable[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        seen: set[int] = set()
        for code in codes:
            m = by_code.get(code.upper())
            if m and id(m) not in seen:
                out.append(m)
                seen.add(id(m))
        for name in names:
            for key, m in by_name.items():
                if name in key and id(m) not in seen:
                    out.append(m)
                    seen.add(id(m))
        return out

    wanted: list[dict[str, Any]] = []
    if source_type == "esat":
        # ESAT specimen modules: maths1, maths2, physics, chemistry, biology
        mod_key = (module or "").lower()
        name_hints = {
            "maths1": ["mathematics 1"],
            "maths2": ["mathematics 2"],
            "physics": ["physics"],
            "chemistry": ["chemistry"],
            "biology": ["biology"],
        }
        codes = {"maths1": "M1", "maths2": "M2", "physics": "P", "chemistry": "C", "biology": "B"}
        wanted = find([codes.get(mod_key, "")], name_hints.get(mod_key, []))
    elif source_type == "tmua":
        sec = (section or "").upper()
        if "P1" in sec:
            wanted = find(["M1"], ["mathematics 1"])
        else:
            wanted = find(["M2"], ["mathematics 2"])
    elif source_type == "engaa":
        wanted = find(["M1", "M2"], ["mathematics 1", "mathematics 2"])
    elif source_type == "nsaa":
        wanted = find(["P", "C", "B"], ["physics", "chemistry", "biology"])
    elif source_type == "nsaa_s2":
        subj = (subject or "").lower()
        codes = {"physics": "P", "chemistry": "C", "biology": "B"}
        wanted = find([codes.get(subj, "")], [subj] if subj else [])

    if not wanted:
        wanted = modules

    lines: list[str] = []
    for m in wanted:
        code = m.get("code", "")
        name = m.get("name", "")
        lines.append(f"### Module {code}: {name}")
        for topic in m.get("topics", []):
            tcode = topic.get("spec_code", "")
            tname = topic.get("name", "")
            lines.append(f"- {tcode} {tname}")
            for sub in topic.get("subtopics", []):
                scode = sub.get("spec_code", "")
                sname = (sub.get("name") or "").strip()
                if scode:
                    lines.append(f"    - {scode} {sname[:120]}")
    return "\n".join(lines) if lines else "(No relevant taxonomy modules found.)"


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------


def detect_corpus_file(path: Path) -> CorpusFile:
    """Detect corpus metadata from path (mirrors anthropic-enrichment.py)."""
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
        parts2 = path.stem.split("_", 1)
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

    return CorpusFile(path=path, source_type=source_type, section=section, subject=subject, module=module)


def load_corpus_files(input_path: Path) -> list[CorpusFile]:
    """Load corpus JSON files from a path (file or directory)."""
    resolved = input_path.resolve()
    if not resolved.exists():
        # Try resolving against CORPUS_DIR
        resolved = (CORPUS_DIR / input_path).resolve()

    files: list[CorpusFile] = []
    if resolved.is_file() and resolved.suffix == ".json" and not resolved.name.endswith(".bak"):
        files.append(detect_corpus_file(resolved))
    elif resolved.is_dir():
        for json_file in sorted(resolved.rglob("*.json")):
            if json_file.name.endswith(".bak"):
                continue
            files.append(detect_corpus_file(json_file))
    else:
        logger.error("Input path %s is not a valid file or directory", input_path)
        sys.exit(1)

    logger.info("Found %d corpus file(s) under %s", len(files), resolved)
    return files


def load_questions(corpus_file: CorpusFile) -> list[dict[str, Any]]:
    with open(corpus_file.path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data:
        return data["questions"]
    if isinstance(data, list):
        return data
    logger.error("Unexpected format in %s", corpus_file.path)
    return []


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """\
You are an expert Cambridge admissions test analyst specialising in the \
Engineering and Science Admissions Test (ESAT). You produce structured \
enrichment data for past paper questions.

## NUMERICAL CONVENTIONS

- Gravitational field strength: g = 10 N kg^-1 (ESAT convention, spec P3.5b). \
  Never use g = 9.81 or 9.8.
- Use standard angles 0, 30, 45, 60, 90 degrees unless the question says otherwise.
- Any constant not listed here must be given in the question stem.

## ESAT CONTENT SPECIFICATION TAXONOMY (relevant module(s))

{taxonomy_block}

Classify each question using the codes above. If the topic cannot be mapped \
to any code above, classify as is_out_of_spec=true and skip the Worked \
Solution and Distractor Analysis.

{nsaa_s2_rule}

## OUTPUT FORMAT

Respond in Markdown with EXACTLY these sections, in this order. Use LaTeX \
($...$ inline, $$...$$ display) for all maths.

## Worked Solution

Step-by-step solution. Each step self-contained (a student reading only \
text must be able to follow — never rely on a diagram to convey essential \
reasoning). Use numbered steps. If a diagram was provided, you may insert \
markers on their own lines at the point where the diagram would help:

[DIAGRAM 1]
[DIAGRAM 2]
(Up to 4 diagrams. Only place markers if a diagram image was provided.)

End your solution with: "The correct answer is **X**." (X = option letter).

If the stated correct answer in the question is WRONG, explain the error \
clearly and state what the correct answer should be.

## Distractor Analysis

For each incorrect option, one bullet explaining the misconception or \
calculation error that leads a student to pick it.

## Classification

- **Module:** (e.g., Mathematics 1, Physics)
- **Module Code:** (e.g., M1, P)
- **Topic Code:** (from the taxonomy above)
- **Topic Name:**
- **Content Code:** (final subtopic code, or OUT_OF_SPEC)
- **Question Type:** (e.g., single-step calculation, multi-step derivation, conceptual)

## Difficulty Rating

Rate difficulty 1-10 (1 = trivial, 10 = very hard for a strong ESAT candidate). \
Then on its own line, exactly:

Difficulty: X/10

And on a final line, exactly:

Difficulty Category: <Easy|Medium|Hard|Very Hard>

Use this mapping as a guide: 1-3 Easy, 4-5 Medium, 6-7 Hard, 8-10 Very Hard.

## OCR Corrections

List any corrections to the OCR-extracted question text, options, or answer. \
Format as a numbered list. Each item: "field: <corrected text> (reason)". \
If the OCR is clean, write exactly:

No OCR corrections needed.

## Diagram Descriptions

For each [DIAGRAM n] marker above, describe what the diagram should show. \
If no diagrams were provided with the question, write exactly:

No diagrams needed.

**IMPORTANT:** Only emit [DIAGRAM n] markers and diagram descriptions if a \
diagram image was explicitly provided with this question.
"""

USER_PROMPT_TEMPLATE = """\
Produce a complete enrichment for this question using the output format \
specified in your system instructions.

### Question
{question_text}

### Options
{options_list}
(Option count varies per question — typically 4 to 8, not always A-E. \
Biology questions commonly have 6 or 8 options.)

### Correct Answer (from OCR answer key)
{correct_answer_letter}
""" + "(If you believe this answer key is wrong, explain in the Worked Solution and OCR Corrections sections.)\n"


NSAA_S2_ACTIVE_RULE = (
    "## NSAA S2 OUT-OF-SPEC FILTERING\n"
    "ACTIVE — This is an NSAA Section 2 question. Classify the topic FIRST. "
    "If the topic cannot be mapped to the ESAT taxonomy above, set Content "
    "Code to OUT_OF_SPEC and skip the Worked Solution and Distractor Analysis."
)


def get_nsaa_s2_rule(corpus_file: CorpusFile) -> str:
    if corpus_file.source_type == "nsaa_s2":
        return NSAA_S2_ACTIVE_RULE
    return ""


def format_options(options: Any) -> str:
    if isinstance(options, dict):
        return "\n".join(f"- {k}: {v}" for k, v in options.items())
    if isinstance(options, list):
        return "\n".join(f"- {i+1}: {v}" for i, v in enumerate(options))
    return str(options)


def build_system_prompt(corpus_file: CorpusFile, taxonomy: dict[str, Any]) -> str:
    block = render_taxonomy_for_module(
        taxonomy,
        source_type=corpus_file.source_type,
        module=corpus_file.module,
        subject=corpus_file.subject,
        section=corpus_file.section,
    )
    rule = get_nsaa_s2_rule(corpus_file)
    prompt = SYSTEM_PROMPT_TEMPLATE.format(taxonomy_block=block, nsaa_s2_rule=rule)
    # Collapse any blank-section artifacts when rule is empty
    if not rule:
        prompt = prompt.replace("\n\n\n\n## OUTPUT FORMAT", "\n\n## OUTPUT FORMAT")
    return prompt


def build_user_prompt(question: dict[str, Any]) -> str:
    qt = question.get("question_text", "") or ""
    options = question.get("options") or {}
    correct = question.get("correct_answer") or question.get("correct_answer_plain") or ""
    return USER_PROMPT_TEMPLATE.format(
        question_text=qt,
        options_list=format_options(options),
        correct_answer_letter=correct,
    )


# ---------------------------------------------------------------------------
# Image handling
# ---------------------------------------------------------------------------


def collect_image_paths(question: dict[str, Any]) -> list[str]:
    """Return list of image relative paths from corpus dir for this question."""
    paths: list[str] = []
    for key in ("diagram_images", "question_images"):
        vals = question.get(key)
        if isinstance(vals, list):
            for v in vals:
                if isinstance(v, str) and v.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                    paths.append(v)
    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def resolve_image_path(rel: str) -> Optional[Path]:
    """Resolve a relative image path under corpus/images/."""
    cands = [
        IMAGES_DIR / rel,
        SHARED_DIR / "corpus" / rel,
        SHARED_DIR / rel,
    ]
    for c in cands:
        if c.exists():
            return c
    return None


def build_image_blocks(image_paths: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for rel in image_paths[:MAX_IMAGES_PER_QUESTION]:
        abs_path = resolve_image_path(rel)
        if abs_path is None:
            logger.warning("Image not found: %s", rel)
            continue
        ext = abs_path.suffix.lower()
        media_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(ext, "image/png")
        with open(abs_path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
        blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        })
    return blocks


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

DIFFICULTY_CATEGORY_PATTERN = re.compile(r"Difficulty\s*Category\s*:\s*(Easy|Medium|Hard|Very\s*Hard)", re.IGNORECASE)
DIFFICULTY_SCORE_PATTERN = re.compile(r"Difficulty\s*:\s*(\d{1,2})\s*/\s*10", re.IGNORECASE)
DIAGRAM_MARKER_PATTERN = re.compile(r"^\s*\[DIAGRAM\s+(\d+)\]\s*$", re.MULTILINE)


def parse_enrichment(markdown: str, corpus_file: CorpusFile) -> dict[str, Any]:
    """Parse the enrichment markdown into structured fields."""
    # Split by ## headers
    parts = re.split(r"^##\s+(.+)$", markdown, flags=re.MULTILINE)
    sections: dict[str, str] = {}
    current: Optional[str] = None
    for i, part in enumerate(parts):
        if i % 2 == 1:
            current = part.strip().lower()
        elif current:
            sections[current] = part.strip()

    classification_text = sections.get("classification", "") or ""
    topic_classification = parse_classification(classification_text, corpus_file)

    difficulty_text = sections.get("difficulty rating", "") or ""
    rating = None
    m = DIFFICULTY_SCORE_PATTERN.search(difficulty_text)
    if m:
        try:
            rating = int(m.group(1))
        except ValueError:
            rating = None
    category = None
    m = DIFFICULTY_CATEGORY_PATTERN.search(difficulty_text)
    if m:
        category = re.sub(r"\s+", " ", m.group(1).title())

    ocr_corrections = parse_ocr_corrections(sections.get("ocr corrections", "") or "")

    is_out_of_spec = (
        topic_classification.get("is_out_of_spec", False)
        or "out_of_spec" in classification_text.lower()
    )

    return {
        "worked_solution": sections.get("worked solution", ""),
        "distractor_analysis": sections.get("distractor analysis", ""),
        "classification": classification_text,
        "difficulty_rating_text": difficulty_text,
        "diagram_descriptions": sections.get("diagram descriptions", ""),
        "difficulty_rating": rating,
        "difficulty_category": category,
        "topic_classification": topic_classification,
        "ocr_corrections": ocr_corrections,
        "is_out_of_spec": is_out_of_spec,
        "has_diagram_markers": bool(DIAGRAM_MARKER_PATTERN.search(sections.get("worked solution", ""))),
    }


def parse_classification(text: str, corpus_file: CorpusFile) -> dict[str, Any]:
    """Extract module/code fields from the Classification section text.

    Handles markdown list lines like ``-   **Module Code:** M1`` by stripping
    list markers and bold wrappers before splitting on the first colon.
    """
    fields: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        # Strip leading list markers: "- ", "* ", "1. ", "1) "
        line = re.sub(r"^(?:\d+[\.\)]\s*|[-*]\s+)", "", line).strip()
        # Strip markdown bold so "**Module Code:**" -> "Module Code:"
        line = line.replace("**", "")
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key_norm = key.strip().lower().replace(" ", "_")
        # Normalise the long content-code label down to "content_code"
        if key_norm.startswith("content_code"):
            key_norm = "content_code"
        val = val.strip()
        if not val:
            continue
        fields[key_norm] = val

    def pick(*keys: str) -> Optional[str]:
        for k in keys:
            if k in fields and fields[k]:
                return str(fields[k])
        return None

    content_code = pick("content_code")
    is_out_of_spec = bool(
        content_code and "out_of_spec" in content_code.lower()
    ) or bool(pick("is_out_of_spec", "out_of_spec"))

    return {
        "module": pick("module"),
        "module_code": pick("module_code"),
        "topic_code": pick("topic_code"),
        "topic_name": pick("topic_name"),
        "content_code": content_code,
        "question_type": pick("question_type"),
        "is_out_of_spec": is_out_of_spec,
    }


def parse_ocr_corrections(text: str) -> list[dict[str, Any]]:
    """Parse the OCR Corrections section into structured items."""
    text = text.strip()
    if not text or text.lower().startswith("no ocr corrections"):
        return []
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(?:\d+[\.\)]\s*|\*\s*|\-\s*)?(.+)$", line)
        if not m:
            continue
        raw = m.group(1).strip().lstrip("*").strip()
        if not raw or raw.lower().startswith("no ocr corrections"):
            continue
        # Split on first colon for field/reason
        if ":" in raw:
            field, _, rest = raw.partition(":")
            # Try to split rest into "corrected (reason)"
            reason = ""
            corrected = rest.strip()
            rm = re.match(r"^(.+?)\s*\((.+)\)\s*$", corrected)
            if rm:
                corrected = rm.group(1).strip()
                reason = rm.group(2).strip()
            items.append({
                "field": field.strip().lstrip("*").strip(),
                "corrected": corrected,
                "reason": reason,
            })
        else:
            items.append({"field": "", "corrected": raw, "reason": ""})
    return items


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------


def call_opus_api(
    client: anthropic.Anthropic,
    system_prompt: str,
    user_prompt: str,
    model: str,
    image_blocks: Optional[list[dict[str, Any]]] = None,
) -> tuple[str, dict[str, int]]:
    """Call Anthropic Messages API with retry. Returns (response_text, token_usage)."""
    content_blocks: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
    if image_blocks:
        content_blocks.extend(image_blocks)

    messages = [{"role": "user", "content": content_blocks}]

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=REQUEST_MAX_TOKENS,
                timeout=REQUEST_TIMEOUT_SECONDS,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
            )
            text = ""
            for block in response.content:
                if getattr(block, "type", "") == "text":
                    text += getattr(block, "text", "")
            usage = {
                "input_tokens": getattr(response.usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(response.usage, "output_tokens", 0) or 0,
                "cache_read_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            }
            return text, usage
        except anthropic.RateLimitError as e:
            last_exc = e
            delay = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1.5)
            logger.warning("Rate limit (attempt %d/%d), retry in %.1fs", attempt + 1, MAX_RETRIES, delay)
            time.sleep(delay)
        except anthropic.APIConnectionError as e:
            last_exc = e
            delay = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1.0)
            logger.warning("Connection error (attempt %d/%d), retry in %.1fs", attempt + 1, MAX_RETRIES, delay)
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            last_exc = e
            # Don't retry on 4xx except 429 (handled above as RateLimitError)
            if 400 <= e.status_code < 500 and e.status_code != 429:
                raise RuntimeError(f"API {e.status_code}: {getattr(e, 'message', str(e))}") from e
            delay = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1.0)
            logger.warning("API %d (attempt %d/%d), retry in %.1fs", e.status_code, attempt + 1, MAX_RETRIES, delay)
            time.sleep(delay)
        except Exception as e:
            last_exc = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Unexpected error (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
            time.sleep(delay)

    raise RuntimeError(f"Exhausted {MAX_RETRIES} retries: {last_exc}")


# ---------------------------------------------------------------------------
# Per-question processing
# ---------------------------------------------------------------------------


def process_question(
    client: anthropic.Anthropic,
    question: dict[str, Any],
    corpus_file: CorpusFile,
    system_prompt: str,
    model: str,
    dry_run: bool = False,
) -> EnrichmentResult:
    qid = question.get("id", "unknown")
    rel_path = str(corpus_file.path.relative_to(CORPUS_DIR))
    user_prompt = build_user_prompt(question)
    image_paths = collect_image_paths(question)

    if dry_run:
        logger.info("[DRY-RUN] %s from %s (images=%d)", qid, rel_path, len(image_paths))
        return EnrichmentResult(
            question_id=qid,
            source_file=rel_path,
            status="success",
            enrichment_markdown="[DRY-RUN] no API call",
        )

    attempts = 0
    start = time.time()
    try:
        image_blocks = build_image_blocks(image_paths) if image_paths else None
        attempts += 1
        text, usage = call_opus_api(client, system_prompt, user_prompt, model, image_blocks=image_blocks)
        parsed = parse_enrichment(text, corpus_file)

        # If parsing found missing core sections, retry once with explicit instruction
        if not parsed["worked_solution"] and attempts < MAX_RETRIES:
            logger.warning("%s: missing Worked Solution, retrying once", qid)
            followup = user_prompt + "\n\nNOTE: Your previous response was missing required sections. Please respond with ALL required sections exactly as specified."
            attempts += 1
            text, usage = call_opus_api(client, system_prompt, followup, model, image_blocks=image_blocks)
            parsed = parse_enrichment(text, corpus_file)

        duration = time.time() - start
        status = "out_of_spec" if parsed["is_out_of_spec"] else "success"

        logger.info(
            "%s: %s (in=%d out=%d %.1fs attempts=%d)",
            qid, status, usage["input_tokens"], usage["output_tokens"], duration, attempts,
        )

        return EnrichmentResult(
            question_id=qid,
            source_file=rel_path,
            status=status,
            enrichment_markdown=text,
            difficulty_rating=parsed["difficulty_rating"],
            difficulty_category=parsed["difficulty_category"],
            topic_classification=parsed["topic_classification"],
            ocr_corrections=parsed["ocr_corrections"],
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cache_read_tokens=usage["cache_read_tokens"],
            cache_creation_tokens=usage["cache_creation_tokens"],
            duration_seconds=duration,
            attempts=attempts,
        )
    except Exception as e:
        duration = time.time() - start
        logger.error("%s: FAILED after %.1fs (%d attempts) — %s", qid, duration, attempts, e)
        return EnrichmentResult(
            question_id=qid,
            source_file=rel_path,
            status="failed",
            error=str(e),
            duration_seconds=duration,
            attempts=attempts,
        )


# ---------------------------------------------------------------------------
# State / resume
# ---------------------------------------------------------------------------


def load_state() -> dict[str, str]:
    """Load the per-question state manifest. Returns {question_id: status}."""
    if not STATE_PATH.exists():
        return {}
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load state from %s: %s — starting fresh", STATE_PATH, e)
        return {}


_state_lock = threading.Lock()


def save_state(state: dict[str, str]) -> None:
    """Persist the state manifest atomically."""
    tmp = STATE_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    tmp.replace(STATE_PATH)


_state_log_lock = threading.Lock()


def append_run_log(record: dict[str, Any]) -> None:
    """Append a single enrichment record to the JSONL run log."""
    RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with _state_log_lock:
        with open(RUN_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)


# ---------------------------------------------------------------------------
# Output writing (per corpus file)
# ---------------------------------------------------------------------------

_output_lock = threading.Lock()


def write_output_for_file(
    corpus_file: CorpusFile,
    original_data: dict[str, Any],
    enriched_by_qid: dict[str, dict[str, Any]],
    output_dir: Path,
    model: str,
) -> Path:
    """Write (or update) the enriched output file for a corpus file.

    Merges freshly enriched questions with any already-on-disk results so
    resuming mid-file doesn't lose work.
    """
    rel = corpus_file.path.relative_to(CORPUS_DIR)
    out_path = output_dir / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing output if present (resume case)
    existing: dict[str, dict[str, Any]] = {}
    if out_path.exists():
        try:
            with open(out_path, encoding="utf-8") as f:
                prev = json.load(f)
            for q in prev.get("questions", []):
                qid = q.get("id")
                if qid:
                    existing[qid] = q
        except Exception:
            pass

    merged_questions: list[dict[str, Any]] = []
    for q in original_data.get("questions", []):
        qid = q.get("id")
        if not qid:
            continue
        fresh = enriched_by_qid.get(qid)
        if fresh is not None:
            merged_questions.append(fresh)
        elif qid in existing:
            merged_questions.append(existing[qid])
        else:
            # Untouched — pass through original
            merged_questions.append(q)

    output_data = dict(original_data)
    output_data["questions"] = merged_questions
    output_data["enriched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    output_data["enrichment_model"] = model

    tmp = out_path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    tmp.replace(out_path)
    return out_path


def build_enriched_question(
    question: dict[str, Any],
    result: EnrichmentResult,
    model: str,
) -> dict[str, Any]:
    """Attach an `enrichment` block to a question, per opus-trial format."""
    enriched = dict(question)
    enrichment: dict[str, Any] = {
        "status": result.status,
        "model": model,
        "enriched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "markdown": result.enrichment_markdown if result.status in ("success", "out_of_spec") else None,
        "difficulty_rating": result.difficulty_rating,
        "difficulty_category": result.difficulty_category,
        "topic_classification": result.topic_classification,
        "ocr_corrections": result.ocr_corrections,
        "error": result.error if result.status == "failed" else None,
        "processor_id": model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "attempts": result.attempts,
        "duration_seconds": round(result.duration_seconds, 2),
    }
    enriched["enrichment"] = enrichment
    return enriched


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------


class CostTracker:
    def __init__(self, model: str) -> None:
        self.model = model
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_tokens = 0
        self.cache_creation_tokens = 0
        self._lock = threading.Lock()

    def add(self, r: EnrichmentResult) -> None:
        with self._lock:
            self.input_tokens += r.input_tokens
            self.output_tokens += r.output_tokens
            self.cache_read_tokens += r.cache_read_tokens
            self.cache_creation_tokens += r.cache_creation_tokens

    def estimate_usd(self) -> float:
        pricing = MODEL_PRICING.get(self.model, {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0})
        regular_input = max(0, self.input_tokens - self.cache_read_tokens - self.cache_creation_tokens)
        return (
            regular_input * pricing["input"] / 1_000_000
            + self.output_tokens * pricing["output"] / 1_000_000
            + self.cache_read_tokens * pricing.get("cache_read", 0.0) / 1_000_000
            + self.cache_creation_tokens * pricing.get("cache_write", 0.0) / 1_000_000
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    global DEFAULT_OUTPUT_DIR, STATE_PATH, RUN_LOG_PATH
    parser = argparse.ArgumentParser(
        description="Batch Opus enrichment pipeline for all ESAT corpus questions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python opus-batch-enrichment.py --dry-run --limit 5
  python opus-batch-enrichment.py --input corpus/json/tmua/specimen_p1.json --limit 2
  python opus-batch-enrichment.py --concurrency 4
  python opus-batch-enrichment.py --reset
        """,
    )
    parser.add_argument("--input", type=Path, default=CORPUS_DIR, help="Corpus file or directory (default: whole corpus)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N questions per file (testing)")
    parser.add_argument("--concurrency", type=int, default=3, help="Parallel workers (default: 3)")
    parser.add_argument("--max-cost-usd", type=float, default=1000.0, help="Halt when estimated cost exceeds this (default: $1000)")
    parser.add_argument("--reset", action="store_true", help="Ignore existing state and re-enrich everything")
    parser.add_argument("--retry-failed", action="store_true", help="Re-attempt questions marked failed in state")
    parser.add_argument("--dry-run", action="store_true", help="Don't call the API; just print prompts and exit")
    parser.add_argument("--api-key", type=str, default=None, help="API key (or set ANTHROPIC_API_KEY)")
    parser.add_argument("--base-url", type=str, default=None, help="API base URL (or set ANTHROPIC_BASE_URL)")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.INFO)

    if args.output_dir != DEFAULT_OUTPUT_DIR:
        DEFAULT_OUTPUT_DIR = args.output_dir
        STATE_PATH = DEFAULT_OUTPUT_DIR / "_state.json"
        RUN_LOG_PATH = DEFAULT_OUTPUT_DIR / "_run_log.jsonl"

    args.output_dir.mkdir(parents=True, exist_ok=True)

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not api_key and not args.dry_run:
        logger.error("ANTHROPIC_API_KEY required for live runs. Set the env var or pass --api-key.")
        sys.exit(1)
    base_url = args.base_url or os.environ.get("ANTHROPIC_BASE_URL")

    client: Optional[anthropic.Anthropic] = None
    if not args.dry_run:
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = anthropic.Anthropic(**client_kwargs)
        logger.info("Anthropic client ready (base_url=%s, model=%s)", base_url or "default", args.model)

    taxonomy = load_taxonomy()
    logger.info("Loaded taxonomy (%d modules)", len(taxonomy.get("modules", [])))

    corpus_files = load_corpus_files(args.input)
    if not corpus_files:
        logger.error("No corpus files found")
        sys.exit(1)

    # Build the global work queue: (corpus_file, question) tuples
    work: list[tuple[CorpusFile, dict[str, Any], dict[str, Any]]] = []
    total_q_count = 0
    for cf in corpus_files:
        with open(cf.path, encoding="utf-8") as f:
            original = json.load(f)
        questions = original.get("questions", []) if isinstance(original, dict) else original
        if args.limit is not None:
            questions = questions[: args.limit]
        for q in questions:
            if not q.get("id") or not q.get("question_text"):
                continue
            work.append((cf, q, original))
            total_q_count += 1
    logger.info("Total questions queued: %d", total_q_count)

    # State handling
    state = {} if args.reset else load_state()
    if args.reset:
        logger.info("--reset: ignoring existing state; re-enriching everything")
    if state:
        done = sum(1 for s in state.values() if s == "success" or s == "out_of_spec")
        logger.info("State: %d already complete, %d to (re)process", done, total_q_count - done)

    # Filter queue by state
    pending: list[tuple[CorpusFile, dict[str, Any], dict[str, Any]]] = []
    skipped_already_done = 0
    for cf, q, original in work:
        qid = q.get("id", "")
        prev = state.get(qid)
        if prev in ("success", "out_of_spec") and not args.reset:
            skipped_already_done += 1
            continue
        if prev == "failed" and not args.retry_failed and not args.reset:
            # leave failed alone unless asked
            continue
        pending.append((cf, q, original))
    logger.info(
        "Pending this run: %d (skipped %d already done)",
        len(pending), skipped_already_done,
    )

    if not pending:
        logger.info("Nothing to do. Exiting.")
        print_summary(state, total_q_count, CostTracker(args.model), args.model, dry_run=args.dry_run)
        return

    # Pre-build system prompts per corpus file (cacheable across questions)
    system_prompts: dict[str, str] = {}
    for cf in corpus_files:
        system_prompts[str(cf.path)] = build_system_prompt(cf, taxonomy)

    # Per-file accumulators (guarded by output lock)
    enriched_by_file: dict[str, dict[str, dict[str, Any]]] = {}
    for cf, _, _ in pending:
        enriched_by_file.setdefault(str(cf.path), {})

    cost = CostTracker(args.model)
    processed_count = 0
    failed_count = 0
    halt = False

    def do_one(item: tuple[CorpusFile, dict[str, Any], dict[str, Any]]) -> EnrichmentResult:
        cf, q, _ = item
        sp = system_prompts[str(cf.path)]
        return process_question(client, q, cf, sp, args.model, dry_run=args.dry_run)

    workers = max(1, args.concurrency)
    logger.info("Running with %d worker(s)", workers)

    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(do_one, item): item for item in pending}
            for fut in as_completed(futures):
                cf, q, _ = futures[fut]
                qid = q.get("id", "unknown")
                try:
                    result = fut.result()
                except Exception as e:
                    result = EnrichmentResult(
                        question_id=qid,
                        source_file=str(cf.path.relative_to(CORPUS_DIR)),
                        status="failed",
                        error=f"worker exception: {e}",
                    )

                processed_count += 1
                if result.status == "failed":
                    failed_count += 1

                # Update state + outputs (never persist during dry-run, otherwise a
                # dry-run would mark questions "success" and cause a real run to skip them).
                if args.dry_run:
                    if processed_count % 25 == 0:
                        logger.info(
                            "[progress] %d/%d dry-run processed, %d failed",
                            processed_count, len(pending), failed_count,
                        )
                    continue

                with _state_lock:
                    state[qid] = result.status
                cost.add(result)
                enriched_q = build_enriched_question(q, result, args.model)
                with _output_lock:
                    enriched_by_file[str(cf.path)][qid] = enriched_q
                append_run_log({
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "question_id": qid,
                    "source_file": result.source_file,
                    "status": result.status,
                    "model": args.model,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "attempts": result.attempts,
                    "duration_seconds": round(result.duration_seconds, 2),
                    "difficulty_rating": result.difficulty_rating,
                    "difficulty_category": result.difficulty_category,
                    "topic_classification": result.topic_classification,
                    "ocr_corrections": result.ocr_corrections,
                    "error": result.error,
                })

                # Periodic state/output flush
                if processed_count % 10 == 0:
                    with _state_lock:
                        save_state(state)
                    flush_outputs_to_disk(corpus_files, enriched_by_file, args.output_dir, args.model)
                    est = cost.estimate_usd()
                    logger.info(
                        "[progress] %d/%d done, %d failed, est cost $%.4f / $%.2f cap",
                        processed_count, len(pending), failed_count, est, args.max_cost_usd,
                    )
                    if est > args.max_cost_usd:
                        logger.error("Cost cap exceeded ($%.4f > $%.2f) — halting", est, args.max_cost_usd)
                        halt = True
                if halt:
                    break
    finally:
        # Final flush (skipped for dry-run — nothing was persisted)
        if not args.dry_run:
            with _state_lock:
                save_state(state)
            flush_outputs_to_disk(corpus_files, enriched_by_file, args.output_dir, args.model)

    print_summary(state, total_q_count, cost, args.model, dry_run=args.dry_run)
    if halt:
        logger.warning("Run halted early due to cost cap. Re-run to resume.")
        sys.exit(2)


def flush_outputs_to_disk(
    corpus_files: list[CorpusFile],
    enriched_by_file: dict[str, dict[str, dict[str, Any]]],
    output_dir: Path,
    model: str,
) -> None:
    """Persist current enriched data per corpus file (resume-safe merge)."""
    with _output_lock:
        for cf in corpus_files:
            file_map = enriched_by_file.get(str(cf.path), {})
            if not file_map:
                continue
            try:
                with open(cf.path, encoding="utf-8") as f:
                    original = json.load(f)
            except Exception:
                continue
            write_output_for_file(cf, original, file_map, output_dir, model)


def print_summary(
    state: dict[str, str],
    total_q_count: int,
    cost: CostTracker,
    model: str,
    dry_run: bool = False,
) -> None:
    success = sum(1 for s in state.values() if s in ("success", "out_of_spec"))
    failed = sum(1 for s in state.values() if s == "failed")
    other = sum(1 for s in state.values() if s not in ("success", "out_of_spec", "failed"))
    remaining = max(0, total_q_count - success)

    print("\n" + "=" * 64)
    print("OPUS BATCH ENRICHMENT — SUMMARY")
    print("=" * 64)
    print(f"  Model:            {model}")
    print(f"  Total questions:  {total_q_count}")
    print(f"  Successful:       {success}")
    print(f"  Failed:           {failed}")
    print(f"  Other/skipped:    {other}")
    print(f"  Remaining:        {remaining}")
    if not dry_run:
        print("-" * 64)
        print(f"  Input tokens:     {cost.input_tokens:,}")
        print(f"  Output tokens:    {cost.output_tokens:,}")
        print(f"  Cache read:       {cost.cache_read_tokens:,}")
        print(f"  Cache write:      {cost.cache_creation_tokens:,}")
        print(f"  Estimated cost:   ${cost.estimate_usd():.4f}")
    print("=" * 64)
    if remaining > 0:
        print(f"Resume: re-run this script to continue from where it stopped.")
    print(f"Output dir: {DEFAULT_OUTPUT_DIR}")
    print(f"State file: {STATE_PATH}")
    print(f"Run log:    {RUN_LOG_PATH}")


if __name__ == "__main__":
    main()
