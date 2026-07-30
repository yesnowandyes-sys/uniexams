#!/usr/bin/env python3
"""
ESA-44 Part B — cross-source deduplication of the corpus.

The corpus contains questions drawn from several exams (ESAT specimen, NSAA,
ENGAA, TMUA). The same question sometimes appears in more than one paper. This
script merges near-duplicate questions into a single primary record, folding
the merged sources into a JSON array and summing their source weights.

Pipeline
--------
1. Ensure `source_weight` (REAL, default 1.0) and `sources` (JSON array)
   columns exist on `questions`.
2. Derive a source weight for every corpus question from its id prefix.
3. Identify the 69 questions flagged `is_out_of_spec:true`
   (enrichment.topic_classification.is_out_of_spec). These are EXCLUDED from
   merging but retained.
4. Normalise question text (strip LaTeX markup, lowercase, collapse
   whitespace).
5. Embed the normalised text with sentence-transformers `all-MiniLM-L6-v2`
   (384-dim) and compute pairwise cosine similarity.
6. Pairs with cosine > THRESHOLD (0.92) are duplicates. Union-Find groups
   transitive duplicates together.
7. For each multi-member group: pick a primary (highest source weight; ties
   broken toward error-free enrichment, then by id), set `source_weight` to the
   summed weights, set `sources` to all member ids, and DELETE the
   non-primary members.
8. Singletons (and out-of-spec rows) get `source_weight` = own weight and
   `sources` = [own id].

The script is **idempotent**. A row whose existing `sources` array already has
more than one entry is treated as a finalised merge primary from a prior run:
it is preserved untouched and excluded from further merging, so re-running
never corrupts earlier work or double-counts weights.

Environment
-----------
Requires `sentence_transformers` + `torch` (CPU is fine) and the
`all-MiniLM-L6-v2` model (cached under ~/.cache/huggingface). On this host a
working env lives at /tmp/arm64-dep-test-venv; to recreate one see
scripts/requirements-dedup.txt.

    /tmp/arm64-dep-test-venv/bin/python scripts/dedup_corpus.py [--db PATH] [--dry-run]

Reference: ESA-44 Part B.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger("dedup_corpus")

DEFAULT_DB = "/home/ubuntu/.paperclip/esat-shared/data/questions.db"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
THRESHOLD = 0.92  # cosine above this => duplicate (ESA-44 Part B step 3)


# ──────────────────────────────────────────────────────────────────────────
# Source weights — derived from the question id prefix (ESA-44 Part B)
# ──────────────────────────────────────────────────────────────────────────

NSAA_S1 = re.compile(r"^NSAA-.*-S1-")
ENGAA_S1 = re.compile(r"^ENGAA-.*-S1-")
NSAA_S2 = re.compile(r"^NSAA-.*-S2-")
TMUA_P1 = re.compile(r"^TMUA-.*-P1-")
TMUA_P2 = re.compile(r"^TMUA-.*-P2-")
ESAT = re.compile(r"^ESAT-")


def source_weight(qid: str, subject: str | None) -> float:
    """Return the canonical weight for a question based on its id prefix.

    - ESAT-*                       = 1.00
    - NSAA-*-S1-*                  = 0.95
    - ENGAA-*-S1-*                 = 0.85
    - TMUA-*-P1-* / TMUA-*-P2-*    = 0.75   (P2 not listed in spec; same
                                             exam family → same weight — see
                                             notes; override if needed)
    - NSAA-*-S2-*                  = 0.75 physics/chemistry, 0.50 biology
    """
    if NSAA_S2.match(qid):
        s = (subject or "").strip().lower()
        if s == "biology":
            return 0.50
        if s in ("physics", "chemistry"):
            return 0.75
        logger.warning("NSAA-S2 question %s has unexpected subject %r; defaulting to 0.75", qid, subject)
        return 0.75
    if NSAA_S1.match(qid):
        return 0.95
    if ENGAA_S1.match(qid):
        return 0.85
    if TMUA_P1.match(qid) or TMUA_P2.match(qid):
        return 0.75
    if ESAT.match(qid):
        return 1.00
    logger.warning("unknown source family for id %r; defaulting weight to 1.0", qid)
    return 1.0


# ──────────────────────────────────────────────────────────────────────────
# Text normalisation (ESA-44 Part B step 1)
# ──────────────────────────────────────────────────────────────────────────

_LATEX_DELIMS = ("\\[", "\\]", "\\(", "\\)", "$")
_CMD = re.compile(r"\\[a-zA-Z]+")  # \frac, \text, \cdot, \times, ...
_MARKS = re.compile(r"[_^{}]")
_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Strip LaTeX markup, lowercase, and collapse whitespace.

    Math delimiters and backslash commands are removed (their arguments kept as
    literal tokens), braces and super/subscript markers become spaces. This
    lets the same question typeset slightly differently across papers embed to
    nearly the same vector.
    """
    if not text:
        return ""
    t = text
    for d in _LATEX_DELIMS:
        t = t.replace(d, " ")
    t = _CMD.sub(" ", t)
    t = _MARKS.sub(" ", t)
    t = t.lower()
    return _WS.sub(" ", t).strip()


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def is_out_of_spec(enrichment_json: str | None) -> bool:
    """True if enrichment.topic_classification.is_out_of_spec is truthy."""
    if not enrichment_json:
        return False
    try:
        e = json.loads(enrichment_json)
    except (ValueError, TypeError):
        return False
    tc = e.get("topic_classification") if isinstance(e, dict) else None
    return bool(isinstance(tc, dict) and tc.get("is_out_of_spec"))


def parse_sources(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        v = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return v if isinstance(v, list) else []


def ensure_columns(con: sqlite3.Connection) -> None:
    cols = {r[1] for r in con.execute("PRAGMA table_info(questions)")}
    if "source_weight" not in cols:
        con.execute("ALTER TABLE questions ADD COLUMN source_weight REAL NOT NULL DEFAULT 1.0")
        logger.info("added column questions.source_weight")
    if "sources" not in cols:
        con.execute("ALTER TABLE questions ADD COLUMN sources TEXT NOT NULL DEFAULT '[]'")
        logger.info("added column questions.sources")


# ──────────────────────────────────────────────────────────────────────────
# Union-Find
# ──────────────────────────────────────────────────────────────────────────

class UF:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────

def primary_key(row: dict) -> tuple:
    """Sort key: higher weight first, then error-free enrichment, then id."""
    has_error = bool(row.get("_enr_error"))
    return (-row["weight"], 1 if has_error else 0, row["id"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--dry-run", action="store_true", help="analyse and report; write nothing")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    db = Path(args.db)
    if not db.exists():
        logger.error("database not found: %s", db)
        return 2

    try:
        import numpy as np  # noqa: F401
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        logger.error(
            "sentence-transformers/torch/numpy not importable (%s). "
            "Use a venv that has them, e.g. /tmp/arm64-dep-test-venv/bin/python. "
            "See scripts/requirements-dedup.txt.",
            exc,
        )
        return 3

    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        ensure_columns(con)

        rows = con.execute(
            "SELECT id, subject, source, question_text, enrichment, sources "
            "FROM questions WHERE source='corpus'"
        ).fetchall()
        logger.info("loaded %d corpus rows", len(rows))

        # Build per-question records.
        recs: list[dict] = []
        out_of_spec_ids: set[str] = set()
        locked_ids: set[str] = set()  # already-finalised merge primaries
        for r in rows:
            oos = is_out_of_spec(r["enrichment"])
            if oos:
                out_of_spec_ids.add(r["id"])
            existing_sources = parse_sources(r["sources"])
            if len(existing_sources) > 1:
                locked_ids.add(r["id"])
            enr_error = False
            if r["enrichment"]:
                try:
                    e = json.loads(r["enrichment"])
                    enr_error = bool(isinstance(e, dict) and e.get("error"))
                except (ValueError, TypeError):
                    enr_error = True
            recs.append(
                {
                    "id": r["id"],
                    "subject": r["subject"],
                    "text": r["question_text"] or "",
                    "weight": source_weight(r["id"], r["subject"]),
                    "oos": oos,
                    "locked": r["id"] in locked_ids,
                    "_enr_error": enr_error,
                    "existing_sources": existing_sources,
                }
            )

        weight_hist: dict[float, int] = {}
        for rec in recs:
            weight_hist[rec["weight"]] = weight_hist.get(rec["weight"], 0) + 1
        logger.info("source-weight distribution: %s", sorted(weight_hist.items()))
        logger.info("out_of_spec (excluded from merge, retained): %d", len(out_of_spec_ids))
        logger.info("locked (prior merge primaries, preserved): %d", len(locked_ids))

        # Participants: corpus minus out-of-spec minus locked.
        parts = [r for r in recs if not r["oos"] and not r["locked"]]
        logger.info("dedup participants: %d", len(parts))

        if not parts:
            logger.warning("no participants to dedup; nothing to do")
            return 0

        # Embed normalised text.
        texts = [normalise(r["text"]) for r in parts]
        empty = [parts[i]["id"] for i, t in enumerate(texts) if not t]
        if empty:
            logger.warning("%d participant(s) normalised to empty text: %s", len(empty), empty[:5])
        logger.info("loading embedding model %s ...", MODEL_NAME)
        model = SentenceTransformer(MODEL_NAME)
        emb = model.encode(
            texts,
            batch_size=64,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        logger.info("embedded %d x %d", emb.shape[0], emb.shape[1])

        # Pairwise cosine (rows already L2-normalised).
        sim = emb @ emb.T
        np.fill_diagonal(sim, -1.0)
        iu, ju = np.where(np.triu(sim > args.threshold, k=1))
        edges = list(zip(iu.tolist(), ju.tolist()))
        logger.info("duplicate pairs (cos > %.2f): %d", args.threshold, len(edges))

        uf = UF(len(parts))
        for a, b in edges:
            uf.union(a, b)
        groups: dict[int, list[int]] = {}
        for i in range(len(parts)):
            groups.setdefault(uf.find(i), []).append(i)

        merge_groups = [g for g in groups.values() if len(g) > 1]
        merged_away = sum(len(g) - 1 for g in merge_groups)
        logger.info(
            "multi-member groups: %d (will merge %d rows into primaries)",
            len(merge_groups),
            merged_away,
        )
        primary_ids_preview: set[str] = set()
        for g in merge_groups:
            members = sorted((parts[i] for i in g), key=primary_key)
            primary_ids_preview.add(members[0]["id"])

        if args.dry_run:
            for gi, g in enumerate(sorted(merge_groups, key=lambda g: -len(g))[:10]):
                members = sorted(parts[i]["id"] for i in g)
                logger.info("[dry-run] group %d (%d): %s ...", gi, len(g), members[:6])
            singleton_or_oos = sum(
                1 for r in recs
                if not r["locked"] and r["id"] not in primary_ids_preview
            )
            logger.info(
                "[dry-run] would delete %d rows, update %d primaries, set weights on %d singletons/oos",
                merged_away,
                len(merge_groups),
                singleton_or_oos,
            )
            return 0

        # Apply.
        cur = con.cursor()
        cur.execute("BEGIN")

        primary_ids_in_groups: set[str] = set()
        deleted_ids: set[str] = set()
        deleted = 0
        updated_primaries = 0
        for g in merge_groups:
            members = [parts[i] for i in g]
            members.sort(key=primary_key)
            primary = members[0]
            others = members[1:]
            all_ids = sorted(m["id"] for m in members)
            summed = round(sum(m["weight"] for m in members), 6)
            cur.execute(
                "UPDATE questions SET source_weight=?, sources=?, updated_at=datetime('now') WHERE id=?",
                (summed, json.dumps(all_ids), primary["id"]),
            )
            updated_primaries += 1
            primary_ids_in_groups.add(primary["id"])
            for o in others:
                cur.execute("DELETE FROM questions WHERE id=?", (o["id"],))
                deleted_ids.add(o["id"])
                deleted += 1

        # Surviving singletons (not locked, not a primary, not deleted) and
        # out-of-spec rows: set their own weight and sources=[own id].
        singletons_set = 0
        for rec in recs:
            if rec["locked"] or rec["id"] in primary_ids_in_groups or rec["id"] in deleted_ids:
                continue
            cur.execute(
                "UPDATE questions SET source_weight=?, sources=?, updated_at=datetime('now') WHERE id=?",
                (round(rec["weight"], 6), json.dumps([rec["id"]]), rec["id"]),
            )
            singletons_set += 1

        con.commit()

        final = con.execute(
            "SELECT (SELECT COUNT(*) FROM questions WHERE source='corpus') AS corpus, "
            "(SELECT COUNT(*) FROM questions WHERE source='corpus' AND json_array_length(sources)>1) AS merged_primaries, "
            "(SELECT COUNT(*) FROM questions WHERE source='corpus' AND source_weight<>1.0) AS nondefault_weight"
        ).fetchone()
        logger.info(
            "after: corpus=%d merged_primaries=%d deleted=%d singletons/oos_set=%d",
            final["corpus"], final["merged_primaries"], deleted, singletons_set,
        )
        logger.info(
            "out_of_spec retained: %d (all kept, excluded from merging)",
            con.execute(
                "SELECT COUNT(*) FROM questions WHERE source='corpus' AND "
                "json_extract(enrichment,'$.topic_classification.is_out_of_spec')=1"
            ).fetchone()[0],
        )
        logger.info("OK: dedup complete.")
        return 0
    except Exception:
        con.rollback()
        logger.exception("dedup failed; transaction rolled back")
        return 1
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
