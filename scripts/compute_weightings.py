#!/usr/bin/env python3
"""
Compute weighted coverage distributions from the enriched corpus — ESA-47.

Reads the enriched corpus (``questions`` rows where ``source != 'generated'``
and the enrichment is not flagged ``is_out_of_spec``), parses the per-question
enrichment JSON, and derives corpus-weighted target proportions for:

* **topic distribution** — within each module, how questions spread across topics,
* **difficulty distribution** — within each module, the Easy/Medium/Hard mix,
* **sub-topic distribution** — within each module, the spread across content codes.

Each corpus question contributes its **source weight** (how closely its origin
exam maps onto the ESAT spec). The weight is taken from the ``source_weight``
column populated by the dedup step (ESA-44) when present: that column is the
**sum of the tier weights of every source merged into the row**, so a row that
represents two ESAT questions carries weight 2.0 rather than 1.0. When the
column is absent (pre-ESA-44 DB) the single-source tier is derived from the
question id:

================  =======  ============================================
Origin            Weight   Notes
================  =======  ============================================
``ESAT-*``        1.00     The target exam itself.
``NSAA-*-S1-*``   0.95     ESAT's direct predecessor.
``ENGAA-*-S1-*``  0.85     ENGAA Section 1.
``TMUA-*-P1-*``   0.75     TMUA paper 1 (maths-only).
``TMUA-*-P2-*``   0.75     TMUA paper 2 (same source tier as P1).
``NSAA-*-S2-*``   0.75     NSAA Section 2 — physics / chemistry.
``NSAA-*-S2-*``   0.50     NSAA Section 2 — biology (derived from module).
================  =======  ============================================

Topics that appear in the ESAT taxonomy but have no corpus questions ("spec-only"
topics) are given a small default weight (1/10 of the average topic weight) so
generation still targets them.

Output: ``data/weightings.json`` consumed by ``coverage_tracker.py``.

Usage::

    python3 compute_weightings.py                 # write data/weightings.json
    python3 compute_weightings.py --report        # also print a summary
    python3 compute_weightings.py --dry-run       # don't write the file

Reference: ``TASKS/02-weighted-coverage.md`` (ESA-47).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SHARED_DIR = Path(__file__).resolve().parent.parent
DB_PATH = SHARED_DIR / "data" / "questions.db"
TAXONOMY_PATH = SHARED_DIR / "esat_taxonomy.json"
OUT_PATH = SHARED_DIR / "data" / "weightings.json"

# Taxonomy module code -> (db module string, spec-topic prefix).
MODULE_CODE_TO_MODULE = {
    "M1": "maths1", "M2": "maths2", "P": "physics", "C": "chemistry", "B": "biology",
}
MODULE_ORDER = ["M1", "M2", "P", "C", "B"]

# The canonical difficulty buckets generation targets (generator only emits
# Easy/Medium/Hard — VALID_DIFFICULTIES). "Very Hard" corpus questions fold
# into Hard so their weight still informs the Hard target.
CANONICAL_DIFFICULTIES = ["Easy", "Medium", "Hard"]

# Small default weight for spec-only topics = SPEC_DEFAULT_FRACTION * average.
SPEC_DEFAULT_FRACTION = 0.10

# Source weights by origin exam (see module docstring table).
WEIGHT_ESAT = 1.00
WEIGHT_NSAA_S1 = 0.95
WEIGHT_ENGAA_S1 = 0.85
WEIGHT_TMUA = 0.75
WEIGHT_NSAA_S2_SCIENCE = 0.75   # physics / chemistry
WEIGHT_NSAA_S2_BIOLOGY = 0.50


# --------------------------------------------------------------------------- #
# Taxonomy helpers
# --------------------------------------------------------------------------- #

def load_taxonomy(path: Path = TAXONOMY_PATH) -> dict[str, Any]:
    """Return ``{module_code: {"name", "topics": {spec_code: {"content_codes": [...]}}}}``."""
    if not path.exists():
        raise FileNotFoundError(f"No taxonomy at {path}")
    raw = json.loads(path.read_text())
    out: dict[str, Any] = {}
    for module in raw.get("modules", []):
        code = module.get("code")
        if code not in MODULE_CODE_TO_MODULE:
            continue
        topics: dict[str, dict[str, Any]] = {}
        for topic in module.get("topics", []):
            spec = topic.get("spec_code")
            if not spec:
                continue
            content_codes = [s.get("spec_code") for s in topic.get("subtopics", [])
                             if s.get("spec_code")]
            topics[spec] = {"name": topic.get("name", ""), "content_codes": content_codes}
        out[code] = {"name": module.get("name", ""), "topics": topics}
    return out


# --------------------------------------------------------------------------- #
# Field normalisation — map noisy LLM-emitted codes to canonical taxonomy codes
# --------------------------------------------------------------------------- #

def normalize_module(module_code: Any, topic_code: Any = None) -> str | None:
    """Map an enrichment ``module_code`` to a canonical code (M1/M2/P/C/B).

    Enrichment ``module_code`` values are LLM-produced and noisy. Exact canonical
    matches are trusted directly; otherwise we fall back to the ``topic_code``
    prefix, which is more reliable (MM* -> M2, M# -> M1, P#/C#/B# as expected).
    Returns ``None`` when no canonical code can be derived.
    """
    def _from_token(tok: str | None) -> str | None:
        if not tok:
            return None
        up = re.sub(r"\([^)]*\)", " ", str(tok).strip()).upper()
        up = re.sub(r"[^A-Z0-9 ]", " ", up)
        # Exact canonical token wins.
        for word in up.split():
            if word in MODULE_CODE_TO_MODULE:
                return word
        # Word-level subject heuristics.
        joined = re.sub(r"\s+", "", up)
        if any(k in joined for k in ("MATHS2", "MATHEMATICS2")):
            return "M2"
        if any(k in joined for k in ("MATHS1", "MATHEMATICS1")):
            return "M1"
        if "PHYS" in joined:
            return "P"
        if "CHEM" in joined:
            return "C"
        if "BIO" in joined:
            return "B"
        return None

    canon = _from_token(module_code)
    if canon:
        return canon
    # Fall back to the topic-code prefix.
    return _module_from_topic(topic_code)


def _module_from_topic(topic_code: Any) -> str | None:
    """Derive a canonical module code from a topic/content code prefix."""
    if not topic_code:
        return None
    s = str(topic_code).strip().upper()
    # Match the leading spec token; pick the first one for multi-code entries.
    m = re.search(r"\b(MM\d+|M\d+|P\d+|C\d+|B\d+)", s)
    if not m:
        return None
    tok = m.group(1)
    if tok.startswith("MM"):
        return "M2"
    if tok.startswith("M"):
        return "M1"
    if tok.startswith("P"):
        return "P"
    if tok.startswith("C"):
        return "C"
    if tok.startswith("B"):
        return "B"
    return None


def normalize_topic(module_code: str, topic_code: Any,
                    valid_topics: set[str]) -> str | None:
    """Snap an enrichment ``topic_code`` to a valid spec_code for the module.

    Handles content-style entries (e.g. ``M4.16`` -> ``M4``) and multi-code
    entries (e.g. ``"M4.16, M2.11"`` -> the first valid token). Returns
    ``None`` when nothing maps to a valid topic.
    """
    if not topic_code:
        return None
    s = str(topic_code).strip().upper()
    for m in re.finditer(r"\b(MM\d+|M\d+|P\d+|C\d+|B\d+)", s):
        tok = m.group(1)
        if tok in valid_topics:
            return tok
    return None


def normalize_content(module_code: str, content_code: Any,
                      valid_content: set[str]) -> str | None:
    """Snap an enrichment ``content_code`` to a valid sub-topic spec_code."""
    if not content_code:
        return None
    s = str(content_code).strip().upper()
    # Content codes look like "M4.17", "P3.1b", "MM1.2" — strip letter suffixes.
    for m in re.finditer(r"\b(MM\d+|M\d+|P\d+|C\d+|B\d+)\.(\d+)", s):
        tok = f"{m.group(1)}.{m.group(2)}"
        if tok in valid_content:
            return tok
    return None


def normalize_difficulty(difficulty: Any) -> str | None:
    """Map an enrichment ``difficulty_category`` to Easy/Medium/Hard or None."""
    if difficulty is None:
        return None
    s = str(difficulty).strip().lower()
    if not s:
        return None
    if s == "easy":
        return "Easy"
    if s in {"medium", "moderate", "standard", "intermediate"}:
        return "Medium"
    if s in {"hard", "very hard"}:
        return "Hard"
    # Phrases / combos — bucket by leading qualifier, then keyword fallback.
    if s.startswith(("easy", "low", "straightforward", "basic")):
        return "Easy"
    if s.startswith(("medium", "moderate", "standard", "intermediate")):
        return "Medium"
    if "very hard" in s:
        return "Hard"
    if "hard" in s:
        return "Hard"
    if "moderate" in s or "medium" in s:
        return "Medium"
    if "easy" in s or "simple" in s:
        return "Easy"
    return None


def source_weight(question_id: str, module_code: str | None) -> float | None:
    """Derive the source weight from the question id.

    Returns ``None`` for ids we cannot classify (these are dropped).
    """
    qid = (question_id or "").upper()
    if qid.startswith("ESAT"):
        return WEIGHT_ESAT
    if qid.startswith("NSAA"):
        if "-S1-" in qid:
            return WEIGHT_NSAA_S1
        if "-S2-" in qid:
            # NSAA Section 2: biology is down-weighted; phys/chem higher.
            return WEIGHT_NSAA_S2_BIOLOGY if module_code == "B" else WEIGHT_NSAA_S2_SCIENCE
        return None
    if qid.startswith("ENGAA"):
        # Only ENGAA Section 1 is in scope (Section 2 is essay/long-answer).
        if "-S1-" in qid:
            return WEIGHT_ENGAA_S1
        return None
    if qid.startswith("TMUA"):
        # Both TMUA papers are maths-only at the same source tier.
        if "-P1-" in qid or "-P2-" in qid:
            return WEIGHT_TMUA
        return None
    return None


def _source_family(question_id: str, module_code: str | None) -> str:
    """Human-readable source bucket for the diagnostic report."""
    qid = (question_id or "").upper()
    if qid.startswith("ESAT"):
        return "ESAT"
    if qid.startswith("NSAA") and "-S2-" in qid:
        return f"NSAA-S2-{'BIO' if module_code == 'B' else 'SCI'}"
    if qid.startswith("NSAA"):
        return "NSAA-S1"
    if qid.startswith("ENGAA"):
        return "ENGAA-S1"
    if qid.startswith("TMUA"):
        return "TMUA"
    return "UNKNOWN"


# --------------------------------------------------------------------------- #
# Corpus reading + weighted counting
# --------------------------------------------------------------------------- #

def _iter_corpus(db: sqlite3.Connection):
    """Yield ``(question_id, source_weight_or_None, enrichment_json_str)``.

    ``source_weight`` is the ESA-44 dedup column (sum of the merged sources'
    tier weights) when present, else ``None`` (pre-ESA-44 DB — the caller falls
    back to deriving the single-source tier from the question id).
    """
    cols = {row[1] for row in db.execute("PRAGMA table_info(questions)")}
    has_source_weight = "source_weight" in cols
    select = ("SELECT id, source_weight, enrichment FROM questions "
              if has_source_weight else
              "SELECT id, NULL, enrichment FROM questions ")
    cur = db.execute(
        select + "WHERE source != 'generated' "
        "AND enrichment IS NOT NULL AND enrichment != ''"
    )
    yield from cur.fetchall()


def _row_weight(question_id: str, module_code: str | None,
                col_weight: Any) -> float | None:
    """Resolve a row's source weight.

    Prefers the ESA-44 ``source_weight`` column (authoritative post-dedup: it
    sums the tier weights of every merged source and applies the NSAA-S2
    biology down-weight even when enrichment is ambiguous). Falls back to the
    single-source tier derived from the question id. Returns ``None`` only when
    neither yields a weight (the row is then dropped as an unknown source).
    """
    if col_weight is not None:
        try:
            w = float(col_weight)
        except (TypeError, ValueError):
            w = 0.0
        if w > 0:
            return w
    return source_weight(question_id, module_code)


def compute_weightings(db_path: Path = DB_PATH, taxonomy_path: Path = TAXONOMY_PATH
                       ) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute the weighted distributions.

    Returns ``(weightings, stats)`` where ``weightings`` matches the
    ``data/weightings.json`` schema and ``stats`` carries diagnostic counters.
    """
    taxonomy = load_taxonomy(taxonomy_path)
    db = sqlite3.connect(db_path)

    # Raw weighted accumulators.
    module_raw: dict[str, float] = defaultdict(float)
    topic_raw: dict[str, dict[str, float]] = {m: defaultdict(float) for m in MODULE_ORDER}
    diff_raw: dict[str, dict[str, float]] = {m: defaultdict(float) for m in MODULE_ORDER}
    sub_raw: dict[str, dict[str, float]] = {m: defaultdict(float) for m in MODULE_ORDER}

    stats = {
        "rows_seen": 0, "excluded_out_of_spec": 0, "unclassifiable_module": 0,
        "unclassifiable_topic": 0, "unclassifiable_difficulty": 0,
        "unknown_source": 0, "parse_errors": 0, "used": 0,
        "weight_from_column": 0, "weight_from_id": 0,
        "source_weighted": defaultdict(float),
    }

    for qid, col_weight, enrichment in _iter_corpus(db):
        stats["rows_seen"] += 1
        try:
            e = json.loads(enrichment)
        except (json.JSONDecodeError, TypeError):
            stats["parse_errors"] += 1
            continue

        tc = e.get("topic_classification") or {}
        if tc.get("is_out_of_spec") is True:
            stats["excluded_out_of_spec"] += 1
            continue

        module_code = normalize_module(tc.get("module_code"), tc.get("topic_code"))
        if module_code is None or module_code not in taxonomy:
            stats["unclassifiable_module"] += 1
            continue

        valid_topics = set(taxonomy[module_code]["topics"].keys())
        valid_content = {cc for t in taxonomy[module_code]["topics"].values()
                         for cc in t["content_codes"]}

        topic = normalize_topic(module_code, tc.get("topic_code"), valid_topics)
        if topic is None:
            # Some enrichment puts the real code in content_code (e.g. "M4.17").
            content = normalize_content(module_code, tc.get("content_code"), valid_content)
            if content is None:
                stats["unclassifiable_topic"] += 1
                continue
            topic = re.match(r"(^[A-Z]+\d+)", content).group(1)

        weight = _row_weight(qid, module_code, col_weight)
        if weight is None:
            stats["unknown_source"] += 1
            continue
        stats["weight_from_column" if col_weight else "weight_from_id"] += 1

        stats["used"] += 1
        stats["source_weighted"][_source_family(qid, module_code)] += weight
        module_raw[module_code] += weight
        topic_raw[module_code][topic] += weight

        difficulty = normalize_difficulty(e.get("difficulty_category"))
        if difficulty is not None:
            diff_raw[module_code][difficulty] += weight
        else:
            stats["unclassifiable_difficulty"] += 1

        content = normalize_content(module_code, tc.get("content_code"), valid_content)
        if content is not None:
            sub_raw[module_code][content] += weight

    db.close()

    # ---- Normalise ------------------------------------------------------- #
    module_weights = _normalise(module_raw, MODULE_ORDER)

    topic_weights: dict[str, dict[str, float]] = {}
    difficulty_weights: dict[str, dict[str, float]] = {}
    sub_topic_weights: dict[str, dict[str, float]] = {}

    for module_code in MODULE_ORDER:
        tax_topics = taxonomy.get(module_code, {}).get("topics", {})
        topic_weights[module_code] = _normalise_with_spec_defaults(
            topic_raw[module_code], list(tax_topics.keys()))

        # Difficulty: normalise over classified difficulties only; if a module
        # has no classifiable difficulty, fall back to the 20/50/30 default.
        if sum(diff_raw[module_code].values()) > 0:
            difficulty_weights[module_code] = _normalise(
                diff_raw[module_code], CANONICAL_DIFFICULTIES)
        else:
            difficulty_weights[module_code] = {
                "Easy": 0.20, "Medium": 0.50, "Hard": 0.30}

        # Sub-topics: emit observed content codes only (spec-only sub-topics
        # inherit their parent topic's default weight at the topic level).
        sub_topic_weights[module_code] = _normalise(sub_raw[module_code], None)

    weightings = {
        "version": 1,
        "generated_from": str(DB_PATH.name),
        "description": (
            "Weighted coverage distribution derived from the enriched corpus "
            "(ESA-47). topic/difficulty/sub_topic weights each sum to 1.0 "
            "within a module."),
        "module_weights": module_weights,
        "topic_weights": topic_weights,
        "difficulty_weights": difficulty_weights,
        "sub_topic_weights": sub_topic_weights,
    }
    stats["source_weighted"] = dict(stats["source_weighted"])
    return weightings, stats


def _normalise(raw: dict[str, float], order: list[str] | None) -> dict[str, float]:
    """Normalise a {key: weight} mapping so values sum to 1.0.

    Only keys with positive weight are emitted. When ``order`` is given, keys
    are emitted in that order (canonical ordering); otherwise sorted by key.
    """
    total = sum(raw.values())
    if total <= 0:
        return {}
    present = {k: v for k, v in raw.items() if v > 0}
    if order:
        keys = [k for k in order if k in present] + sorted(k for k in present if k not in order)
    else:
        keys = sorted(present)
    return {k: round(present[k] / total, 6) for k in keys}


def _normalise_with_spec_defaults(raw: dict[str, float],
                                  all_topics: list[str]) -> dict[str, float]:
    """Normalise topic weights, assigning spec-only topics a small default.

    Spec-only topics (in the taxonomy but absent from the corpus) get a weight
    of ``SPEC_DEFAULT_FRACTION`` times the average observed topic weight, then
    everything is re-normalised so the module sums to 1.0.
    """
    observed = {k: v for k, v in raw.items() if v > 0}
    if not observed:
        # No corpus data for this module — equal weight across all topics.
        n = len(all_topics) or 1
        return {k: round(1.0 / n, 6) for k in all_topics}

    total = sum(observed.values())
    weighted = {k: v / total for k, v in observed.items()}
    n_observed = len(observed)
    avg_weight = 1.0 / n_observed
    default_weight = SPEC_DEFAULT_FRACTION * avg_weight

    spec_only = [t for t in all_topics if t not in observed]
    for t in spec_only:
        weighted[t] = default_weight

    # Re-normalise to 1.0.
    grand = sum(weighted.values())
    return {k: round(v / grand, 6) for k, v in sorted(weighted.items())}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _report(weightings: dict[str, Any], stats: dict[str, Any]) -> None:
    print("== compute_weightings report ==")
    print(f"  corpus rows seen:        {stats['rows_seen']}")
    print(f"  excluded out-of-spec:    {stats['excluded_out_of_spec']}")
    print(f"  unclassifiable module:   {stats['unclassifiable_module']}")
    print(f"  unclassifiable topic:    {stats['unclassifiable_topic']}")
    print(f"  unclassifiable difficulty:{stats['unclassifiable_difficulty']}")
    print(f"  unknown source:          {stats['unknown_source']}")
    print(f"  parse errors:            {stats['parse_errors']}")
    print(f"  questions used:          {stats['used']}")
    print(f"  weight from column:      {stats['weight_from_column']}")
    print(f"  weight from id (fallback):{stats['weight_from_id']}")
    print()
    print("  module_weights:")
    for m in MODULE_ORDER:
        print(f"    {m}: {weightings['module_weights'].get(m, 0.0)}")
    print()
    for m in MODULE_ORDER:
        tw = weightings["topic_weights"].get(m, {})
        dw = weightings["difficulty_weights"].get(m, {})
        sw = weightings["sub_topic_weights"].get(m, {})
        n_spec_only = sum(1 for k, v in tw.items() if v <= 0.0011)
        print(f"  [{m}] topics={len(tw)} (spec-only≈{n_spec_only}) "
              f"sub_topics={len(sw)} difficulty={dw}")
        top = sorted(tw.items(), key=lambda kv: -kv[1])[:5]
        print(f"       top topics: {top}")


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compute ESAT weighted coverage (ESA-47)")
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--taxonomy", type=Path, default=TAXONOMY_PATH)
    p.add_argument("--out", type=Path, default=OUT_PATH)
    p.add_argument("--report", action="store_true", help="Print a summary report")
    p.add_argument("--dry-run", action="store_true", help="Don't write the output file")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    weightings, stats = compute_weightings(args.db, args.taxonomy)
    weightings["generated_from"] = args.db.name

    if args.report:
        _report(weightings, stats)

    if not args.dry_run:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(weightings, indent=2) + "\n")
        logger.info("Wrote %d module distributions to %s", len(MODULE_ORDER), args.out)
    else:
        logger.info("Dry run — weightings not written")

    return 0


if __name__ == "__main__":
    sys.exit(_main())
