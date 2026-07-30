#!/usr/bin/env python3
"""
Biology Factual-Judge Gate (gate 6 of the quality stack).

LLM-as-judge factual check against the ESAT Biology Content Specification
PDF, loaded as static context. The PDF is sent once with Anthropic prompt
caching (`cache_control: ephemeral`) so subsequent calls pay only the
cache_read rate — keeping cost at ~$0.0005 / question (ESA-22 acceptance).

Standard verdict dict:

    {
        "pass": bool,
        "score": float,        # 1.0 consistent, 0.0 inconsistent, 0.5 unsolvable
        "reason": str,
        "issues": list[str],   # factual concerns raised by the judge
        "cost_usd": float,
        "cached_context": bool,
    }
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
    from _llm import call_haiku, DEFAULT_MODEL  # type: ignore
else:
    from .verdict import verdict  # type: ignore
    from ._llm import call_haiku, DEFAULT_MODEL  # type: ignore

logger = logging.getLogger(__name__)


# Where to find the ESAT Biology Content Specification.
DEFAULT_SPEC_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "corpus" / "esat_guides" / "ESAT_Guide_Biology.pdf"
)
# Allow override via env var.
SPEC_PATH_ENV = os.environ.get("ESAT_BIO_SPEC_PATH")
# Pre-extracted full taxonomy (includes the Bio section).
DEFAULT_TAXONOMY_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "esat_taxonomy_summary.txt"
)


JUDGE_SYSTEM_PROMPT_TEMPLATE = """\
You are a Biology examiner reviewing a draft ESAT Biology question for \
factual correctness. Use ONLY the ESAT Biology Content Specification \
provided below as the authoritative source — do not bring in outside \
knowledge beyond standard A-level Biology that is consistent with the spec.

ESAT BIOLOGY CONTENT SPECIFICATION (loaded context):
<<<SPEC
{spec_text}
SPEC>>>

Judge whether every factual claim in the question stem, options, and \
worked solution is consistent with the specification. Output one of:

VERDICT: CONSISTENT
or
VERDICT: INCONSISTENT
<one-line description of the contradiction>

or, if you genuinely cannot tell:

VERDICT: UNSOLVABLE

Do not output anything else.
"""


# ---------------------------------------------------------------------------
# Spec loading + caching
# ---------------------------------------------------------------------------

_SPEC_CACHE: Optional[str] = None


def _load_spec_text(path: Path | None = None) -> str:
    """Load the Bio Content Spec text.

    Prefers a pre-extracted `.txt` next to the PDF; falls back to the
    shipped `esat_taxonomy_summary.txt` Biology section; then to a
    `pdftotext` extraction; finally to a placeholder that defers to
    downstream gates.
    """
    global _SPEC_CACHE
    if _SPEC_CACHE is not None:
        return _SPEC_CACHE

    candidate = Path(path or SPEC_PATH_ENV or DEFAULT_SPEC_PATH)
    txt = candidate.with_suffix(".txt")
    if txt.exists():
        _SPEC_CACHE = txt.read_text(encoding="utf-8", errors="replace")[:60_000]
        return _SPEC_CACHE

    # Fallback: pull the Bio section out of the shipped taxonomy summary.
    if DEFAULT_TAXONOMY_PATH.exists():
        full = DEFAULT_TAXONOMY_PATH.read_text(encoding="utf-8", errors="replace")
        # Slice from the Biology module header to the next module (or EOF).
        match = re.search(
            r"MODULE: Biology\b.*?(?=\n─{5,}|\Z)",
            full,
            re.DOTALL,
        )
        if match:
            _SPEC_CACHE = match.group(0)[:60_000]
            return _SPEC_CACHE

    # Fallback: shell out to pdftotext (poppler) if installed.
    import shutil
    import subprocess
    if shutil.which("pdftotext") and candidate.exists():
        try:
            res = subprocess.run(
                ["pdftotext", "-layout", str(candidate), "-"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if res.stdout.strip():
                _SPEC_CACHE = res.stdout[:60_000]
                return _SPEC_CACHE
        except Exception as exc:  # pragma: no cover
            logger.warning("bio_judge: pdftotext extraction failed: %s", exc)

    # Fallback: pdfplumber if installed.
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(candidate) as pdf:  # type: ignore[attr-defined]
            chunks: list[str] = []
            for page in pdf.pages[:30]:  # cap for token budget
                t = page.extract_text() or ""
                if t:
                    chunks.append(t)
            _SPEC_CACHE = "\n".join(chunks)[:60_000] or ""
        if _SPEC_CACHE:
            return _SPEC_CACHE
    except Exception as exc:  # pragma: no cover
        logger.warning("bio_judge: pdfplumber extraction failed: %s", exc)

    # Last resort: defer gracefully.
    _SPEC_CACHE = "[ESAT Biology Content Spec not available — defer to UNSOLVABLE.]"
    return _SPEC_CACHE


# ---------------------------------------------------------------------------
# Core gate
# ---------------------------------------------------------------------------

VERDICT_CONSISTENT = re.compile(r"VERDICT:\s*CONSISTENT", re.IGNORECASE)
VERDICT_INCONSISTENT = re.compile(r"VERDICT:\s*INCONSISTENT\s*(.*)", re.IGNORECASE)
VERDICT_UNSOLVABLE = re.compile(r"VERDICT:\s*UNSOLVABLE", re.IGNORECASE)


def _format_options(options: Any) -> str:
    if isinstance(options, dict):
        return "\n".join(f"  {k}. {v}" for k, v in options.items())
    if isinstance(options, list):
        letters = "ABCDE"
        return "\n".join(f"  {letters[i]}. {v}" for i, v in enumerate(options))
    return str(options)


def _build_user_prompt(question: dict[str, Any]) -> str:
    options_str = _format_options(question.get("options"))
    solution = question.get("worked_solution") or question.get("explanation") or ""
    return (
        f"Stated correct answer: {question.get('correct_answer', 'unknown')}\n\n"
        f"Question:\n{question.get('question_text', '').strip()}\n\n"
        f"Options:\n{options_str}\n\n"
        f"Worked solution:\n{solution.strip()}\n"
    )


def check(
    question: dict[str, Any],
    *,
    spec_path: Path | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Judge Biology factual claims against the Content Spec."""
    spec_text = _load_spec_text(spec_path)
    cached = not spec_text.startswith("[ESAT Biology Content Spec not available")

    system_prompt = JUDGE_SYSTEM_PROMPT_TEMPLATE.format(spec_text=spec_text)

    try:
        result = call_haiku(
            user_prompt=_build_user_prompt(question),
            system_prompt=system_prompt,
            model=model or DEFAULT_MODEL,
            max_tokens=256,
            cache_system_prompt=True,  # ← cached across all bio questions
            temperature=0.0,
        )
    except Exception as exc:
        logger.error("bio_judge Haiku call failed: %s", exc)
        return verdict(
            passed=False,
            score=0.0,
            reason=f"bio_judge API call failed: {exc}",
            issues=[str(exc)],
            cost_usd=0.0,
            gate="bio_judge",
            cached_context=False,
        )

    text = result.text.strip()
    if VERDICT_UNSOLVABLE.search(text):
        return verdict(
            passed=True,
            score=0.5,
            reason="judge returned UNSOLVABLE",
            issues=[],
            cost_usd=result.cost_usd,
            gate="bio_judge",
            cached_context=cached,
        )
    inconsistent = VERDICT_INCONSISTENT.search(text)
    if inconsistent:
        detail = inconsistent.group(1).strip()
        return verdict(
            passed=False,
            score=0.0,
            reason=f"factual inconsistency: {detail or 'unspecified'}",
            issues=[detail or "judge flagged inconsistency"],
            cost_usd=result.cost_usd,
            gate="bio_judge",
            cached_context=cached,
        )
    if VERDICT_CONSISTENT.search(text):
        return verdict(
            passed=True,
            score=1.0,
            reason="all claims consistent with spec",
            issues=[],
            cost_usd=result.cost_usd,
            gate="bio_judge",
            cached_context=cached,
        )
    return verdict(
        passed=True,
        score=0.5,
        reason="judge returned unparseable verdict — treating as unsolvable",
        issues=[f"raw: {text[:300]!r}"],
        cost_usd=result.cost_usd,
        gate="bio_judge",
        cached_context=cached,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_question(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data:
        return data["questions"][0]
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT biology factual judge gate")
    p.add_argument("--question", type=Path)
    p.add_argument("--spec", type=Path, help="Override Bio Content Spec PDF path")
    p.add_argument("--model", default=None)
    args = p.parse_args(argv)

    if not args.question:
        p.error("--question is required")
    question = _load_question(args.question)
    result = check(question, spec_path=args.spec, model=args.model)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
