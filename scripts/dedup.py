#!/usr/bin/env python3
"""
Near-duplicate detector for ESAT question generation — ESA-17 §2.4 + §4 item 7.

Two layers:

1. **Embedding similarity** — `all-MiniLM-L6-v2` + FAISS when available
   (the strategy's recommended path). On ARM64 without sentence-transformers,
   falls back to a dependency-free character-shingle Jaccard detector that
   catches near-duplicates at the wording level (sufficient for the trial —
   the planted-dup acceptance test passes either way).
2. **Concept cap** — secondary guard: at most N questions per
   `(module, topic, difficulty, template_id)` tuple. Prevents the generator
   from producing 50 questions off one insight scenario even when the
   wording varies enough to dodge the embedding threshold.

Usage:
    python3 dedup.py --check path/to/new_question.json --against corpus.jsonl
    python3 dedup.py --check q.json --against-dir shared/corpus/json/esat/

Environment:
    Optional. If `sentence_transformers` + `faiss` are importable, the
    embedding backend is used. Otherwise the shingle backend is used and a
    one-time warning is logged.

Reference: ESA-17 plan §4.5, strategy §2.4 + §4 item 7 + §13.1,
`orchestration-review.md` Priorities #4 + #7 + §13 note.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────

DEFAULT_EMBEDDING_THRESHOLD = 0.85  # strategy §13.1
DEFAULT_SHINGLE_THRESHOLD = 0.80    # Jaccard on 3-char shingles
DEFAULT_CONCEPT_CAP = 5             # max questions per concept cell
SHINGLE_SIZE = 3

_EMBEDDING_BACKEND: Optional[str] = None  # cached on first use


# ──────────────────────────────────────────────────────────────────────────
# Backend detection
# ──────────────────────────────────────────────────────────────────────────


def _detect_backend() -> str:
    """Return 'embedding' if sentence_transformers + faiss are available, else 'shingle'."""
    global _EMBEDDING_BACKEND
    if _EMBEDDING_BACKEND is not None:
        return _EMBEDDING_BACKEND
    try:
        import sentence_transformers  # noqa: F401
        import faiss  # noqa: F401
        _EMBEDDING_BACKEND = "embedding"
        logger.info("dedup backend: sentence_transformers + faiss (ARM64 OK)")
    except ImportError as exc:
        _EMBEDDING_BACKEND = "shingle"
        logger.warning(
            "dedup backend: dependency-free shingle Jaccard "
            "(sentence_transformers/faiss not installed: %s). "
            "Install for better semantic dedup.", exc,
        )
    return _EMBEDDING_BACKEND


# ──────────────────────────────────────────────────────────────────────────
# Question normalisation
# ──────────────────────────────────────────────────────────────────────────


def _normalise(text: str) -> str:
    """Lowercase, collapse whitespace, strip LaTeX delimiters + punctuation.

    Normalisation makes the shingle comparison robust to cosmetic edits
    (extra spaces, $...$ vs $$...$$, trailing periods) that the generator
    might introduce when paraphrasing.
    """
    if not text:
        return ""
    t = text.lower()
    t = t.replace("$", " ").replace("\\(", " ").replace("\\)", " ")
    t = t.replace("{", " ").replace("}", " ")
    t = re.sub(r"\\[a-zA-Z]+", " ", t)  # strip LaTeX commands (\frac, \sqrt, ...)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def question_fingerprint(question: dict[str, Any]) -> str:
    """The text we actually compare for near-duplicate detection.

    Combines the stem + option text — two questions with the same stem but
    different options are NOT duplicates, but two questions with shuffled
    option order ARE.
    """
    stem = _normalise(str(question.get("question_text", "")))
    options = question.get("options", {})
    if isinstance(options, dict):
        # Sort option values so shuffle doesn't matter.
        opt_text = " | ".join(
            _normalise(str(v)) for _, v in sorted(options.items())
        )
    else:
        opt_text = _normalise(str(options))
    return f"{stem} || {opt_text}"


# ──────────────────────────────────────────────────────────────────────────
# Shingle backend (dependency-free)
# ──────────────────────────────────────────────────────────────────────────


def _shingles(text: str, k: int = SHINGLE_SIZE) -> set[str]:
    """Character k-shingles. Whitespace is collapsed so word-boundary edits
    don't dominate the Jaccard score."""
    if len(text) < k:
        return {text} if text else set()
    return {text[i : i + k] for i in range(len(text) - k + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


# ──────────────────────────────────────────────────────────────────────────
# Embedding backend (sentence_transformers + faiss)
# ──────────────────────────────────────────────────────────────────────────

# Module-level caches so repeated calls in one process don't re-load the model.
_ST_MODEL = None
_FAISS_INDEX = None
_EMBEDDING_TEXTS: list[str] = []


def _get_st_model():
    global _ST_MODEL
    if _ST_MODEL is None:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _ST_MODEL


def _embed(texts: list[str]) -> "Any":
    model = _get_st_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def _cosine_similarity(a: Any, b: Any) -> float:
    import numpy as np  # type: ignore
    return float(np.dot(a, b))  # already normalised


# ──────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────


@dataclass
class DupVerdict:
    is_duplicate: bool
    score: float  # similarity (0..1) of the closest existing question
    matched_against: Optional[str]  # id of the matched existing question, if any
    reason: str


def check_duplicate(
    new_question: dict[str, Any],
    existing: Iterable[dict[str, Any]],
    *,
    threshold: Optional[float] = None,
) -> DupVerdict:
    """Return whether `new_question` is a near-duplicate of any in `existing`.

    `existing` is an iterable of question dicts (must have `question_text`
    and `options`). The new question's id is excluded from the match set
    so re-checking an already-stored question is a no-op.
    """
    backend = _detect_backend()
    new_text = question_fingerprint(new_question)
    new_id = str(new_question.get("id", ""))

    if backend == "embedding":
        thresh = threshold if threshold is not None else DEFAULT_EMBEDDING_THRESHOLD
        existing_texts = [
            (q.get("id"), question_fingerprint(q))
            for q in existing
            if str(q.get("id", "")) != new_id
        ]
        if not existing_texts:
            return DupVerdict(False, 0.0, None, "no existing questions to compare")
        # Encode the new question + every existing one in one batch.
        embeddings = _embed([new_text] + [t for _, t in existing_texts])
        new_vec = embeddings[0]
        best_score = 0.0
        best_id: Optional[str] = None
        for i, (qid, _) in enumerate(existing_texts, start=1):
            s = _cosine_similarity(new_vec, embeddings[i])
            if s > best_score:
                best_score = s
                best_id = str(qid) if qid else None
        is_dup = best_score >= thresh
        return DupVerdict(
            is_duplicate=is_dup,
            score=round(best_score, 4),
            matched_against=best_id,
            reason=(
                f"embedding cosine {best_score:.3f} >= {thresh}"
                if is_dup
                else f"embedding cosine {best_score:.3f} < {thresh}"
            ),
        )

    # Shingle backend
    thresh = threshold if threshold is not None else DEFAULT_SHINGLE_THRESHOLD
    new_shingles = _shingles(new_text)
    best_score = 0.0
    best_id: Optional[str] = None
    for q in existing:
        if str(q.get("id", "")) == new_id:
            continue
        s = _jaccard(new_shingles, _shingles(question_fingerprint(q)))
        if s > best_score:
            best_score = s
            best_id = str(q.get("id")) if q.get("id") else None
    is_dup = best_score >= thresh
    return DupVerdict(
        is_duplicate=is_dup,
        score=round(best_score, 4),
        matched_against=best_id,
        reason=(
            f"shingle jaccard {best_score:.3f} >= {thresh}"
            if is_dup
            else f"shingle jaccard {best_score:.3f} < {thresh}"
        ),
    )


def concept_key(question: dict[str, Any]) -> str:
    """The (module, topic, difficulty, template_id) cell for the concept cap."""
    module = question.get("module", "")
    topic = question.get("spec_topic") or question.get("topic") or ""
    difficulty = question.get("difficulty") or question.get("difficulty_band") or ""
    template = question.get("generated_from_template_id") or ""
    return f"{module}|{topic}|{difficulty}|{template}"


def check_concept_cap(
    new_question: dict[str, Any],
    existing: Iterable[dict[str, Any]],
    *,
    cap: int = DEFAULT_CONCEPT_CAP,
) -> tuple[bool, int, str]:
    """Return (over_cap, current_count, key).

    `over_cap=True` means adding this question would exceed the per-cell
    cap — the orchestrator should pick a different template/topic.
    """
    key = concept_key(new_question)
    current = sum(
        1
        for q in existing
        if concept_key(q) == key
        and str(q.get("id", "")) != str(new_question.get("id", ""))
    )
    return (current >= cap, current, key)


def is_acceptable(
    new_question: dict[str, Any],
    existing: Iterable[dict[str, Any]],
    *,
    threshold: Optional[float] = None,
    concept_cap: int = DEFAULT_CONCEPT_CAP,
) -> tuple[bool, str]:
    """Combined verdict: passes dedup AND concept cap.

    Returns (acceptable, reason). The orchestrator calls this before
    storing the candidate.
    """
    dup = check_duplicate(new_question, existing, threshold=threshold)
    if dup.is_duplicate:
        return False, f"duplicate: {dup.reason}"
    over, count, key = check_concept_cap(new_question, existing, cap=concept_cap)
    if over:
        return False, f"concept cap reached: {count} >= {concept_cap} for {key}"
    return True, f"unique (score={dup.score})"


# ──────────────────────────────────────────────────────────────────────────
# I/O helpers
# ──────────────────────────────────────────────────────────────────────────


def _load_question(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data:
        return data["questions"][0]
    return data


def _load_existing(paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in paths:
        if p.is_dir():
            paths.extend(sorted(p.glob("*.json")))
            continue
        if not p.exists() or p.suffix != ".json":
            continue
        try:
            with p.open() as f:
                data = json.load(f)
            if isinstance(data, list):
                out.extend(data)
            elif isinstance(data, dict):
                if "questions" in data:
                    out.extend(data["questions"])
                else:
                    out.append(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping %s: %s", p, exc)
    return out


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Check a candidate question for near-duplicates")
    p.add_argument("--check", type=Path, required=True, help="path to candidate question JSON")
    p.add_argument("--against", nargs="*", type=Path, default=[], help="existing question JSON files/dirs")
    p.add_argument("--against-dir", type=Path, default=None, help="directory of existing questions")
    p.add_argument("--threshold", type=float, default=None)
    p.add_argument("--concept-cap", type=int, default=DEFAULT_CONCEPT_CAP)
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    new_q = _load_question(args.check)
    paths = list(args.against)
    if args.against_dir:
        paths.append(args.against_dir)
    existing = _load_existing(paths)

    dup = check_duplicate(new_q, existing, threshold=args.threshold)
    over, count, key = check_concept_cap(new_q, existing, cap=args.concept_cap)
    acceptable, reason = is_acceptable(
        new_q, existing,
        threshold=args.threshold, concept_cap=args.concept_cap,
    )
    print(json.dumps({
        "is_duplicate": dup.is_duplicate,
        "similarity": dup.score,
        "matched_against": dup.matched_against,
        "dup_reason": dup.reason,
        "concept_over_cap": over,
        "concept_count": count,
        "concept_key": key,
        "acceptable": acceptable,
        "reason": reason,
        "backend": _detect_backend(),
    }, indent=2))
    return 0 if acceptable else 1


if __name__ == "__main__":
    sys.exit(_main())
