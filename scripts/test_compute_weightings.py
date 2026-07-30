#!/usr/bin/env python3
"""
Hermetic unit tests for ``compute_weightings.py`` (ESA-47).

Covers the regression-prone pure helpers (normalisation, difficulty folding,
the source-weight tier table) and the column-vs-id weighting decision, plus a
mini end-to-end run against an in-memory DB + tiny taxonomy so the whole
pipeline is exercised without touching the live corpus.

Run directly::

    python3 scripts/test_compute_weightings.py

or with pytest from the repo root::

    python3 -m pytest scripts/test_compute_weightings.py -q
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

# Allow running from anywhere — import the sibling module.
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import compute_weightings as cw  # noqa: E402


# --------------------------------------------------------------------------- #
# Normalisation helpers
# --------------------------------------------------------------------------- #

def test_normalise_sums_to_one() -> None:
    out = cw._normalise({"A": 1.0, "B": 3.0}, None)
    assert set(out) == {"A", "B"}
    assert abs(out["A"] - 0.25) < 1e-9
    assert abs(out["B"] - 0.75) < 1e-9
    assert abs(sum(out.values()) - 1.0) < 1e-9


def test_normalise_drops_zero_and_empty() -> None:
    assert cw._normalise({}, None) == {}
    assert cw._normalise({"A": 0.0}, None) == {}


def test_normalise_respects_order() -> None:
    out = cw._normalise({"B": 1.0, "A": 1.0}, ["A", "B"])
    assert list(out) == ["A", "B"]


def test_spec_default_is_small_and_sums_to_one() -> None:
    # Topic C is spec-only (no corpus weight); it must get a small default and
    # the module must still sum to 1.0.
    out = cw._normalise_with_spec_defaults({"A": 9.0, "B": 1.0}, ["A", "B", "C"])
    assert abs(sum(out.values()) - 1.0) < 1e-9
    assert out["C"] > 0.0
    # default is 1/10 of the average observed weight, so it is the smallest.
    assert out["C"] < out["B"] < out["A"]


def test_spec_default_no_corpus_equal_split() -> None:
    out = cw._normalise_with_spec_defaults({}, ["X", "Y"])
    assert abs(sum(out.values()) - 1.0) < 1e-9
    assert abs(out["X"] - 0.5) < 1e-9


# --------------------------------------------------------------------------- #
# Field normalisation
# --------------------------------------------------------------------------- #

def test_difficulty_folding() -> None:
    assert cw.normalize_difficulty("easy") == "Easy"
    assert cw.normalize_difficulty("Medium") == "Medium"
    assert cw.normalize_difficulty("moderate") == "Medium"
    assert cw.normalize_difficulty("Very Hard") == "Hard"  # folds into Hard
    assert cw.normalize_difficulty("hard") == "Hard"
    assert cw.normalize_difficulty(None) is None
    assert cw.normalize_difficulty("nonsense") is None


def test_topic_and_module_snapping() -> None:
    assert cw.normalize_module("M1") == "M1"
    assert cw.normalize_module("Maths 2") == "M2"
    assert cw.normalize_module(None, "MM1.2") == "M2"  # falls back to topic prefix
    assert cw.normalize_topic("M1", "M4.16", {"M1", "M4"}) == "M4"
    assert cw.normalize_topic("M1", "garbage", {"M1", "M4"}) is None
    assert cw.normalize_content("M1", "M4.17", {"M4.17"}) == "M4.17"


# --------------------------------------------------------------------------- #
# Source-weight tier table + column-vs-id decision
# --------------------------------------------------------------------------- #

def test_source_weight_tier_table() -> None:
    assert cw.source_weight("ESAT-2024-Q1", "M1") == 1.00
    assert cw.source_weight("NSAA-2020-S1-Q1", "M1") == 0.95
    assert cw.source_weight("NSAA-2020-S2-Q1", "P") == 0.75   # science
    assert cw.source_weight("NSAA-2020-S2-Q1", "B") == 0.50   # biology
    assert cw.source_weight("ENGAA-2016-S1-Q1", "P") == 0.85
    assert cw.source_weight("TMUA-specimen-P1-Q1", "M1") == 0.75
    assert cw.source_weight("TMUA-specimen-P2-Q1", "M1") == 0.75
    assert cw.source_weight("BOGUS-Q1", "M1") is None


def test_row_weight_prefers_column_then_falls_back() -> None:
    # ESA-44 column wins when present and positive (carries merged multiplicity).
    assert cw._row_weight("ESAT-x", "M1", 2.0) == 2.0
    # Fallback to the id-derived tier when the column is missing...
    assert cw._row_weight("ESAT-x", "M1", None) == 1.0
    # ...or non-positive...
    assert cw._row_weight("ESAT-x", "M1", 0.0) == 1.0
    # ...and to None only when neither yields a weight.
    assert cw._row_weight("BOGUS-x", "M1", None) is None


# --------------------------------------------------------------------------- #
# Mini end-to-end against an in-memory DB + tiny taxonomy
# --------------------------------------------------------------------------- #

_MINI_TAXONOMY = {
    "modules": [
        {"code": "M1", "name": "Maths 1", "topics": [
            {"spec_code": "M1", "subtopics": [{"spec_code": "M1.1"}]},
            {"spec_code": "M4", "subtopics": [{"spec_code": "M4.1"}]},
        ]},
        {"code": "M2", "name": "Maths 2", "topics": [
            {"spec_code": "MM1", "subtopics": [{"spec_code": "MM1.1"}]},
        ]},
        {"code": "P", "name": "Physics", "topics": [
            {"spec_code": "P3", "subtopics": [{"spec_code": "P3.1"}]},
        ]},
        {"code": "C", "name": "Chemistry", "topics": [
            {"spec_code": "C1", "subtopics": [{"spec_code": "C1.1"}]},
        ]},
        {"code": "B", "name": "Biology", "topics": [
            {"spec_code": "B3", "subtopics": [{"spec_code": "B3.1"}]},
        ]},
    ]
}


def _enr(module: str, topic: str, content: str, difficulty: str,
        out_of_spec: bool = False) -> str:
    return json.dumps({
        "topic_classification": {
            "module_code": module, "topic_code": topic,
            "content_code": content, "is_out_of_spec": out_of_spec,
        },
        "difficulty_category": difficulty,
    })


def _build_db(path: Path) -> None:
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE questions (id TEXT, source TEXT, source_weight REAL, "
        "enrichment TEXT)"
    )
    rows = [
        # M1: a single ESAT (weight 1.0) and a merged row (weight 2.0) on M4,
        # plus one Easy on M1. M4 must outweigh M1 because of the merge.
        ("ESAT-2024-Q1", "esat", 1.0, _enr("M1", "M4", "M4.1", "Medium")),
        ("ESAT-2024-Q2", "esat", 2.0, _enr("M1", "M4", "M4.1", "Hard")),
        ("ESAT-2024-Q3", "esat", 1.0, _enr("M1", "M1", "M1.1", "Easy")),
        # Out-of-spec — must be excluded from weighting.
        ("ESAT-2024-Q9", "esat", 1.0, _enr("M1", "M4", "M4.1", "Easy", True)),
        # M2 single row.
        ("TMUA-2020-P1-Q1", "tmua", 0.75, _enr("M2", "MM1", "MM1.1", "Medium")),
    ]
    db.executemany("INSERT INTO questions VALUES (?,?,?,?)", rows)
    db.commit()
    db.close()


def test_end_to_end_mini_corpus(tmp_path: Path) -> None:
    db_path = tmp_path / "mini.db"
    tax_path = tmp_path / "tax.json"
    tax_path.write_text(json.dumps(_MINI_TAXONOMY))
    _build_db(db_path)

    weightings, stats = cw.compute_weightings(db_path, tax_path)

    # Out-of-spec excluded; 4 usable rows.
    assert stats["excluded_out_of_spec"] == 1
    assert stats["used"] == 4
    assert stats["unknown_source"] == 0
    # Column supplied the weight for every row in this fixture.
    assert stats["weight_from_column"] == 4
    assert stats["weight_from_id"] == 0

    # Every present distribution sums to 1.0.
    assert abs(sum(weightings["module_weights"].values()) - 1.0) < 1e-6
    for kind in ("topic_weights", "difficulty_weights", "sub_topic_weights"):
        for mod, dist in weightings[kind].items():
            if dist:
                assert abs(sum(dist.values()) - 1.0) < 1e-6, (kind, mod, dist)

    # The merged M4 row (column weight 2.0) makes M4 outweigh M1 within M1.
    m1t = weightings["topic_weights"]["M1"]
    assert m1t["M4"] > m1t["M1"]

    # M1's observed sub-topics are M4.1 (Q1/Q2) and M1.1 (Q3).
    assert set(weightings["sub_topic_weights"]["M1"]) == {"M4.1", "M1.1"}


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #

def _run() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        import inspect
        params = inspect.signature(t).parameters
        if params:  # pytest-style fixture (tmp_path)
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                t(Path(d))
        else:
            t()
        passed += 1
        print(f"  ok  {t.__name__}")
    print(f"\n{passed}/{len(tests)} tests passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(_run())
