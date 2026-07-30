#!/usr/bin/env python3
"""
Coverage tracker for ESAT nightly generation — ESA-24 / ESA-17 §4.5 + §13.2,
extended for corpus-weighted distributions (ESA-47).

Target distribution source priority:

1. ``data/weightings.json`` (ESA-47) — topic / difficulty / sub-topic weights
   derived from the *actual enriched corpus* by ``compute_weightings.py``.
   Topic weights vary within a module (e.g. Algebra > Probability) and the
   difficulty mix varies per module (e.g. physics skews Easy) instead of the
   flat equal-weight / 20-50-30 defaults.
2. ``coverage_targets.json`` (Opus-produced) — flat target list, used as-is.
3. Taxonomy + the 20/50/30 difficulty mix + equal module split — the original
   sane default, built on the fly if neither file is present.

Counts how many *generated* questions per ``(module, topic, difficulty)``
tuple already exist, then picks the next most under-represented tuple.
Sub-topic (``content_code``) coverage is reported alongside.

Usage:
    python3 coverage_tracker.py                     # next tuple to generate
    python3 coverage_tracker.py --summary           # full coverage table
    python3 coverage_tracker.py --sub-topics        # sub-topic (content_code) view
    python3 coverage_tracker.py --mock counts.json  # run against mock counts

Reference: ESA-17 plan §4.5, strategy §2.4 + §13.2 + §13.3,
``orchestration-review.md`` §14, ``TASKS/02-weighted-coverage.md`` (ESA-47).
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SHARED_DIR = Path(__file__).resolve().parent.parent
DB_PATH = SHARED_DIR / "data" / "questions.db"
TARGETS_PATH = SHARED_DIR / "coverage_targets.json"
WEIGHTINGS_PATH = SHARED_DIR / "data" / "weightings.json"
TAXONOMY_PATH = SHARED_DIR / "esat_taxonomy.json"

# Strategy §13.3 target difficulty mix (fallback only — ESA-47 overrides this
# per module from the corpus-weighted difficulty distribution).
DEFAULT_DIFFICULTY_MIX = {"Easy": 0.20, "Medium": 0.50, "Hard": 0.30, "Very Hard": 0.00}

# Per-module weighting. Equal split across the 5 ESAT modules is kept as an
# editorial choice (ESAT coverage should stay balanced regardless of how the
# extraction corpus happened to be sampled). The corpus-derived cross-module
# proportions live in weightings.json["module_weights"] as metadata and can be
# opted into with USE_CORPUS_MODULE_MIX below.
DEFAULT_MODULE_MIX = {
    "maths1": 0.20, "maths2": 0.20, "physics": 0.20,
    "chemistry": 0.20, "biology": 0.20,
}

# Opt into the corpus-derived cross-module mix instead of the equal default.
USE_CORPUS_MODULE_MIX = False

# Taxonomy module code -> (db module string, spec-topic prefix) — matches the
# keys used in weightings.json and the generation_attempts.spec_topic format.
MODULE_CODE_MAP = {
    "M1": ("maths1", "MATHS1"),
    "M2": ("maths2", "MATHS2"),
    "P": ("physics", "PHYS"),
    "C": ("chemistry", "CHEM"),
    "B": ("biology", "BIO"),
}

# spec_topic prefix -> module string (matches generator.spec_to_module).
PREFIX_TO_MODULE = {
    "MATHS1": "maths1", "MATHS2": "maths2", "PHYS": "physics",
    "CHEM": "chemistry", "BIO": "biology",
}


@dataclass
class CoverageTuple:
    """A single (module, topic, difficulty) coverage cell."""

    module: str
    topic: str
    difficulty: str
    target_pct: float
    current_count: int
    target_count: int  # target_pct * grand_target_total

    @property
    def shortfall(self) -> int:
        return max(0, self.target_count - self.current_count)

    @property
    def fill_ratio(self) -> float:
        """0..1 — how close this cell is to its target."""
        if self.target_count <= 0:
            return 1.0
        return min(1.0, self.current_count / self.target_count)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "target_pct": self.target_pct,
            "current_count": self.current_count,
            "target_count": self.target_count,
            "shortfall": self.shortfall,
            "fill_ratio": round(self.fill_ratio, 3),
        }


# --------------------------------------------------------------------------- #
# Target loading
# --------------------------------------------------------------------------- #

def load_weightings(path: Path = WEIGHTINGS_PATH) -> dict[str, Any] | None:
    """Load the corpus-weighted distributions, or None if absent/malformed."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        logger.warning("weightings.json malformed at %s — ignoring", path)
        return None
    if not isinstance(data, dict) or "topic_weights" not in data:
        return None
    return data


def _module_mix(weightings: dict[str, Any] | None) -> dict[str, float]:
    """Resolve the cross-module mix (equal default, or corpus-weighted)."""
    if USE_CORPUS_MODULE_MIX and weightings:
        mw = weightings.get("module_weights", {})
        resolved = {}
        for module_code, mix in mw.items():
            mapping = MODULE_CODE_MAP.get(module_code)
            if mapping:
                resolved[mapping[0]] = mix
        if resolved:
            return resolved
    return DEFAULT_MODULE_MIX


def _targets_from_weightings(weightings: dict[str, Any]) -> list[dict[str, Any]]:
    """Build (module, topic, difficulty, target_pct) cells from weightings.json.

    target_pct = module_mix × topic_weight[module][topic] × difficulty_weight[module][diff]
    so the corpus drives the within-module topic and difficulty spread.
    """
    topic_weights = weightings.get("topic_weights", {})
    difficulty_weights = weightings.get("difficulty_weights", {})
    module_mix = _module_mix(weightings)

    targets: list[dict[str, Any]] = []
    for module_code, tw in topic_weights.items():
        mapping = MODULE_CODE_MAP.get(module_code)
        if not mapping:
            continue
        module, prefix = mapping
        mod_mix = module_mix.get(module, 0.0)
        if mod_mix <= 0:
            continue
        dw = difficulty_weights.get(module_code) or DEFAULT_DIFFICULTY_MIX
        for topic_code, t_pct in tw.items():
            if t_pct <= 0:
                continue
            topic = f"{prefix}.{topic_code}"
            for diff, d_pct in dw.items():
                if d_pct <= 0:
                    continue
                targets.append({
                    "module": module,
                    "topic": topic,
                    "difficulty": diff,
                    "target_pct": round(mod_mix * t_pct * d_pct, 6),
                })
    return targets


def _default_targets() -> list[dict[str, Any]]:
    """Build a flat target list from the taxonomy + default mixes.

    Each (module, topic, difficulty) cell gets a target_pct equal to
    module_mix × (1/num_topics) × difficulty_mix. The grand total sums
    to ~1.0 across all cells.

    Topic is the canonical pattern-dir spec_code (e.g. "MATHS1.M1",
    "PHYS.P5", "CHEM.C11", "BIO.B9") — matches generation_attempts.spec_topic.
    """
    if not TAXONOMY_PATH.exists():
        logger.warning("No taxonomy at %s; using empty target list", TAXONOMY_PATH)
        return []
    tax = json.loads(TAXONOMY_PATH.read_text())
    targets: list[dict[str, Any]] = []
    for module in tax.get("modules", []):
        code = module.get("code")
        mapping = MODULE_CODE_MAP.get(code)
        if not mapping:
            continue
        mod_str, mod_prefix = mapping
        mod_mix = DEFAULT_MODULE_MIX.get(mod_str, 0.0)
        topics = module.get("topics", [])
        if not topics:
            continue
        per_topic = mod_mix / len(topics)
        for t in topics:
            spec = t.get("spec_code", "")
            if not spec:
                continue
            # Pattern dirs use "{PREFIX}.{SPEC}" e.g. MATHS1.M1, PHYS.P5.
            topic = f"{mod_prefix}.{spec}"
            for diff, diff_pct in DEFAULT_DIFFICULTY_MIX.items():
                if diff_pct <= 0:
                    continue
                targets.append({
                    "module": mod_str,
                    "topic": topic,
                    "difficulty": diff,
                    "target_pct": round(per_topic * diff_pct, 6),
                })
    return targets


def load_targets(path: Path = TARGETS_PATH) -> list[dict[str, Any]]:
    """Load coverage targets, or build defaults if absent.

    Priority: data/weightings.json (ESA-47) > coverage_targets.json (Opus) >
    taxonomy defaults. Schema for the produced list:
    [{"module": str, "topic": str, "difficulty": str, "target_pct": float}, ...]
    """
    # 1. Corpus-weighted distributions (ESA-47).
    weightings = load_weightings(WEIGHTINGS_PATH)
    if weightings:
        targets = _targets_from_weightings(weightings)
        if targets:
            logger.info("Loaded %d corpus-weighted targets from %s",
                        len(targets), WEIGHTINGS_PATH)
            return targets
        logger.warning("weightings.json present but produced no targets — falling back")

    # 2. Opus-produced flat targets.
    if path.exists():
        data = json.loads(path.read_text())
        if isinstance(data, dict) and "targets" in data:
            data = data["targets"]
        if isinstance(data, list) and data:
            logger.info("Loaded %d coverage targets from %s", len(data), path)
            return data
        logger.warning("coverage_targets.json empty/malformed at %s — using defaults", path)
    else:
        logger.info("No coverage_targets.json at %s — building defaults from taxonomy", path)

    # 3. Taxonomy + default mixes.
    return _default_targets()


# --------------------------------------------------------------------------- #
# Generated-question counting
# --------------------------------------------------------------------------- #

def _has_difficulty_column(db: sqlite3.Connection) -> bool:
    """True if generation_attempts records a difficulty column.

    The canonical schema (import-corpus.ts) does not include one, but some
    flows (nightly_run.py) insert it. We degrade gracefully either way.
    """
    cols = {row[1] for row in db.execute("PRAGMA table_info(generation_attempts)")}
    return "difficulty" in cols


def _count_generated(db: sqlite3.Connection) -> dict[tuple[str, str, str], int]:
    """Return {(module, topic, difficulty): count} for accepted generated questions.

    Counts come from ``generation_attempts`` (status='accepted'). Topic is the
    attempt's spec_topic (e.g. "MATHS1.M1"); module is derived from its prefix.

    When ``generation_attempts`` has no ``difficulty`` column (the current
    canonical schema), difficulty is unknown and the count is tagged with an
    empty difficulty string (""). ``compute_coverage`` then falls back to that
    topic-level count so coverage math still works.
    """
    counts: dict[tuple[str, str, str], int] = {}

    if _has_difficulty_column(db):
        cur = db.execute(
            "SELECT spec_topic, difficulty, COUNT(*) FROM generation_attempts "
            "WHERE status = 'accepted' AND spec_topic IS NOT NULL "
            "GROUP BY spec_topic, difficulty"
        )
        for spec_topic, difficulty, n in cur.fetchall():
            if not spec_topic:
                continue
            prefix = spec_topic.split(".", 1)[0].upper()
            module = PREFIX_TO_MODULE.get(prefix, "")
            if not module:
                continue
            key = (module, spec_topic, difficulty or "")
            counts[key] = counts.get(key, 0) + n
    else:
        logger.info("generation_attempts has no difficulty column — "
                    "counting generated questions at topic level")
        cur = db.execute(
            "SELECT spec_topic, COUNT(*) FROM generation_attempts "
            "WHERE status = 'accepted' AND spec_topic IS NOT NULL "
            "GROUP BY spec_topic"
        )
        for spec_topic, n in cur.fetchall():
            if not spec_topic:
                continue
            prefix = spec_topic.split(".", 1)[0].upper()
            module = PREFIX_TO_MODULE.get(prefix, "")
            if not module:
                continue
            key = (module, spec_topic, "")
            counts[key] = counts.get(key, 0) + n
    return counts


def _count_generated_sub_topics(db: sqlite3.Connection) -> dict[tuple[str, str], int]:
    """Return {(module, content_code): count} for generated questions.

    Reads ``content_code`` from the enrichment JSON of generated questions
    (source='generated'). Most generated questions are not yet enriched, so
    this returns an empty map today; the path exists for when generation
    records content codes.
    """
    counts: dict[tuple[str, str], int] = {}
    try:
        cur = db.execute(
            "SELECT module, enrichment FROM questions "
            "WHERE source = 'generated' AND enrichment IS NOT NULL AND enrichment != ''"
        )
    except sqlite3.OperationalError:
        return counts
    for module, enrichment in cur.fetchall():
        try:
            tc = (json.loads(enrichment) or {}).get("topic_classification") or {}
        except (json.JSONDecodeError, TypeError):
            continue
        content_code = (tc.get("content_code") or "").strip().upper()
        if not content_code or not module:
            continue
        counts[(module, content_code)] = counts.get((module, content_code), 0) + 1
    return counts


# --------------------------------------------------------------------------- #
# Coverage computation
# --------------------------------------------------------------------------- #

def compute_coverage(
    targets: list[dict[str, Any]],
    *,
    generated_counts: dict[tuple[str, str, str], int] | None = None,
    db: sqlite3.Connection | None = None,
    grand_target_total: int = 1000,
) -> list[CoverageTuple]:
    """Compute CoverageTuple for every target cell.

    `grand_target_total` is the eventual corpus size we're aiming at
    (1,000 by default — strategy §Phase 3).
    """
    if generated_counts is None:
        if db is None:
            db = sqlite3.connect(DB_PATH)
        generated_counts = _count_generated(db)
    out: list[CoverageTuple] = []
    for t in targets:
        key = (t["module"], t["topic"], t["difficulty"])
        cur = generated_counts.get(key)
        if cur is None:
            # Difficulty not recorded for this question — fall back to the
            # topic-level ("") count so the cell still reflects real fill.
            cur = generated_counts.get((t["module"], t["topic"], ""), 0)
        tgt = int(round(t.get("target_pct", 0.0) * grand_target_total))
        out.append(CoverageTuple(
            module=t["module"], topic=t["topic"], difficulty=t["difficulty"],
            target_pct=t.get("target_pct", 0.0),
            current_count=cur, target_count=tgt,
        ))
    return out


def pick_next(
    coverage: list[CoverageTuple],
    *,
    top_k: int = 1,
) -> list[CoverageTuple]:
    """Pick the most under-represented tuple(s).

    Ties broken by: largest absolute shortfall first, then alphabetically
    for determinism. Cells with zero target are skipped.
    """
    candidates = [c for c in coverage if c.target_count > 0]
    candidates.sort(key=lambda c: (
        c.fill_ratio,            # least-filled first
        -c.shortfall,            # then by largest shortfall desc
        c.module, c.topic, c.difficulty,
    ))
    return candidates[:top_k]


# --------------------------------------------------------------------------- #
# Sub-topic (content_code) view — ESA-47
# --------------------------------------------------------------------------- #

def sub_topic_targets(
    weightings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Expand weightings.json sub_topic_weights into target cells.

    Returns [{"module", "topic", "content_code", "target_pct"}, ...] where
    target_pct is the within-module sub-topic proportion.
    """
    if weightings is None:
        weightings = load_weightings(WEIGHTINGS_PATH) or {}
    cells: list[dict[str, Any]] = []
    for module_code, sw in weightings.get("sub_topic_weights", {}).items():
        mapping = MODULE_CODE_MAP.get(module_code)
        if not mapping:
            continue
        module, prefix = mapping
        for content_code, pct in sw.items():
            if pct <= 0:
                continue
            topic_code = str(content_code).split(".", 1)[0]
            cells.append({
                "module": module,
                "topic": f"{prefix}.{topic_code}",
                "content_code": str(content_code),
                "target_pct": round(pct, 6),
            })
    return cells


def compute_sub_topic_coverage(
    *,
    db: sqlite3.Connection | None = None,
    grand_target_total: int = 1000,
) -> list[dict[str, Any]]:
    """Coverage per content_code — target proportion vs generated count."""
    weightings = load_weightings(WEIGHTINGS_PATH) or {}
    cells = sub_topic_targets(weightings)
    if not cells:
        return []
    if db is None:
        db = sqlite3.connect(DB_PATH)
    counts = _count_generated_sub_topics(db)
    out: list[dict[str, Any]] = []
    for c in cells:
        cur = counts.get((c["module"], c["content_code"]), 0)
        tgt = int(round(c["target_pct"] * grand_target_total))
        out.append({
            "module": c["module"],
            "topic": c["topic"],
            "content_code": c["content_code"],
            "target_pct": c["target_pct"],
            "current_count": cur,
            "target_count": tgt,
        })
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT coverage tracker")
    p.add_argument("--summary", action="store_true",
                   help="Print the full coverage table instead of just next-pick")
    p.add_argument("--sub-topics", action="store_true",
                   help="Print the sub-topic (content_code) coverage view")
    p.add_argument("--top-k", type=int, default=1,
                   help="How many under-represented tuples to list")
    p.add_argument("--mock", type=Path, default=None,
                   help="Use mock generated-counts JSON instead of the DB")
    p.add_argument("--grand-total", type=int, default=1000,
                   help="Target corpus size (default 1000)")
    p.add_argument("--targets", type=Path, default=TARGETS_PATH,
                   help="Override coverage_targets.json path (not weightings.json)")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    targets = load_targets(args.targets)
    if args.mock:
        mock = json.loads(args.mock.read_text())
        # {"counts": [{"module": ..., "topic": ..., "difficulty": ..., "count": ...}, ...]}
        counts: dict[tuple[str, str, str], int] = {}
        for row in mock.get("counts", mock if isinstance(mock, list) else []):
            counts[(row["module"], row["topic"], row["difficulty"])] = row["count"]
        coverage = compute_coverage(targets, generated_counts=counts,
                                    grand_target_total=args.grand_total)
    else:
        db = sqlite3.connect(DB_PATH)
        coverage = compute_coverage(targets, db=db,
                                    grand_target_total=args.grand_total)
        if args.sub_topics:
            sub = compute_sub_topic_coverage(db=db, grand_target_total=args.grand_total)
            print(json.dumps({"sub_topic_coverage": sub}, indent=2))
            db.close()
            return 0
        db.close()

    if args.summary:
        out = [c.to_dict() for c in coverage]
        print(json.dumps({"targets_count": len(out), "coverage": out}, indent=2))
        return 0

    picks = pick_next(coverage, top_k=args.top_k)
    print(json.dumps([p.to_dict() for p in picks], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
