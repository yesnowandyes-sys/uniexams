#!/usr/bin/env python3
"""
FAISS Deduplication Gate — Layer 5 of the verification stack (ESA-45).

Every newly generated question is checked against ALL existing questions
(corpus + previously generated) before it is accepted:

1. Embed the new question text with sentence-transformers `all-MiniLM-L6-v2`
   (384-dim, CPU).
2. Compare against a FAISS `IndexFlatIP` of every existing question embedding
   (vectors are L2-normalised, so inner product == cosine similarity).
3. **Cosine similarity > 0.85 → REJECT** as a near-duplicate.
4. Maintain a **concept-level cap**: no more than `cap` (default 30) accepted
   questions per `(module, topic_code, difficulty)` cell. If the cell is full,
   the gate rejects so the generator moves on to an under-represented cell.

The index is built once from the corpus (`build_index`) and stored under
`data/faiss_index/`. It is updated incrementally as questions are accepted
(`DedupIndex.add`) so intra-batch and cross-run near-duplicates are caught.

Standard verdict dict:

    {
        "pass": bool,            # False on near-duplicate or cap hit
        "score": float,          # 1.0 unique, 0.0 dup/cap
        "reason": str,
        "issues": list[str],
        "cost_usd": 0.0,         # all-local, no API call
        "gate": "dedup_check",
        "max_similarity": float, # best cosine to any existing question
        "nearest_id": str | None,
    }

Usage:
    python dedup_check.py build                    # build the corpus index
    python dedup_check.py --question path/to/q.json
    python dedup_check.py --self-test
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verdict import verdict  # type: ignore
else:
    from .verdict import verdict  # type: ignore

logger = logging.getLogger(__name__)

SHARED_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = SHARED_DIR / "data" / "questions.db"
INDEX_DIR = SHARED_DIR / "data" / "faiss_index"
INDEX_PATH = INDEX_DIR / "index.faiss"
META_PATH = INDEX_DIR / "meta.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.85
DEFAULT_CAP = 30
EMBED_DIM = 384

_model = None


def _get_model():
    """Lazy singleton for the sentence-transformers encoder."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformer %s ...", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(text: str) -> np.ndarray:
    """Embed a single text and L2-normalise → unit vector (cosine-ready)."""
    vec = _get_model().encode([text], normalize_embeddings=True)
    return np.asarray(vec[0], dtype=np.float32)


def embed_many(texts: list[str]) -> np.ndarray:
    """Embed a batch and normalise. Returns shape (n, 384)."""
    if not texts:
        return np.zeros((0, EMBED_DIM), dtype=np.float32)
    vecs = _get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype=np.float32)


# ---------------------------------------------------------------------------
# Concept-level cap
# ---------------------------------------------------------------------------

def _question_cell(question: dict[str, Any]) -> tuple[str, str, str]:
    """Derive the (module, topic_code, difficulty) cap cell from a question.

    Generated questions carry their target cell as `spec_topic` + `difficulty`
    (+ `module`). Corpus/enriched questions carry it under enrichment; we fall
    back to module-level if a finer key is absent.
    """
    module = str(question.get("module") or "").strip()
    topic = (
        question.get("topic_code")
        or question.get("spec_topic")
        or question.get("spec_code")
        or ""
    )
    topic = str(topic).strip()
    difficulty = str(
        question.get("difficulty")
        or question.get("difficulty_band")
        or question.get("difficulty_category")
        or ""
    ).strip()
    return module, topic, difficulty


def _cell_count(db_path: Path, module: str, topic: str, difficulty: str) -> int:
    """Count accepted generated questions already in this cap cell.

    Counts rows where source='generated', module matches, and the stored
    metadata cell (spec_topic + difficulty_band) matches. Topic is matched
    against metadata.spec_topic (set by nightly_run on accept).
    """
    if not db_path.exists():
        return 0
    db = sqlite3.connect(str(db_path))
    try:
        row = db.execute(
            """SELECT COUNT(*) FROM questions
               WHERE source='generated'
                 AND module = ?
                 AND LOWER(IFNULL(json_extract(metadata,'$.spec_topic'),'')) = LOWER(?)
                 AND LOWER(IFNULL(json_extract(metadata,'$.difficulty_band'),'')) = LOWER(?)""",
            (module, topic, difficulty),
        ).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        # metadata column absent / malformed in this DB — treat as empty cell.
        return 0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# DedupIndex — FAISS wrapper with incremental add
# ---------------------------------------------------------------------------

class DedupIndex:
    """A normalised FAISS IndexFlatIP over all existing question texts."""

    def __init__(self) -> None:
        import faiss  # imported lazily so --self-test works without it
        self._faiss = faiss
        self.index = faiss.IndexFlatIP(EMBED_DIM)
        self.ids: list[str] = []
        self.texts: list[str] = []

    def __len__(self) -> int:
        return len(self.ids)

    def add(self, qid: str, text: str, vec: Optional[np.ndarray] = None) -> None:
        """Add one question to the index (used after acceptance)."""
        if vec is None:
            vec = embed(text)
        self.index.add(vec.reshape(1, -1).astype(np.float32))
        self.ids.append(qid)
        self.texts.append(text)

    def add_many(self, ids: list[str], texts: list[str], vecs: np.ndarray) -> None:
        self.index.add(np.asarray(vecs, dtype=np.float32))
        self.ids.extend(ids)
        self.texts.extend(texts)

    def search(self, vec: np.ndarray) -> tuple[float, Optional[str]]:
        """Return (best_cosine, nearest_id) for a single query vector."""
        if len(self) == 0:
            return 0.0, None
        sims, idx = self.index.search(vec.reshape(1, -1).astype(np.float32), 1)
        best = float(sims[0][0])
        nid = self.ids[idx[0][0]] if idx[0][0] >= 0 else None
        return best, nid

    def save(self, index_path: Path = INDEX_PATH, meta_path: Path = META_PATH) -> None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        self._faiss.write_index(self.index, str(index_path))
        meta_path.write_text(json.dumps({"ids": self.ids, "texts": self.texts}))

    @classmethod
    def load(cls, index_path: Path = INDEX_PATH, meta_path: Path = META_PATH) -> "DedupIndex":
        import faiss
        obj = cls()
        obj.index = faiss.read_index(str(index_path))
        meta = json.loads(meta_path.read_text())
        obj.ids = list(meta.get("ids", []))
        obj.texts = list(meta.get("texts", []))
        return obj


def _load_index(db_path: Path = DEFAULT_DB) -> DedupIndex:
    """Load the on-disk index, or build it on first use."""
    if INDEX_PATH.exists() and META_PATH.exists():
        return DedupIndex.load()
    logger.info("No FAISS index at %s — building from corpus", INDEX_PATH)
    idx = build_index(db_path=db_path, out_dir=INDEX_DIR)
    return idx


# ---------------------------------------------------------------------------
# Corpus index build
# ---------------------------------------------------------------------------

def _existing_questions(db_path: Path) -> list[tuple[str, str]]:
    """Return [(id, question_text), ...] for every corpus + generated question."""
    db = sqlite3.connect(str(db_path))
    try:
        rows = db.execute(
            "SELECT id, question_text FROM questions WHERE question_text IS NOT NULL "
            "AND TRIM(question_text) != '' ORDER BY id"
        ).fetchall()
    finally:
        db.close()
    return [(r[0], r[1]) for r in rows]


def build_index(
    db_path: Path = DEFAULT_DB,
    out_dir: Path = INDEX_DIR,
    *,
    batch_size: int = 256,
) -> DedupIndex:
    """Build a FAISS index over all existing questions and persist it."""
    questions = _existing_questions(db_path)
    if not questions:
        logger.warning("No questions in %s — building an empty index", db_path)

    idx = DedupIndex()
    for start in range(0, len(questions), batch_size):
        chunk = questions[start:start + batch_size]
        ids = [q[0] for q in chunk]
        texts = [q[1] for q in chunk]
        vecs = embed_many(texts)
        idx.add_many(ids, texts, vecs)
        logger.info("Indexed %d/%d questions", start + len(chunk), len(questions))

    out_dir.mkdir(parents=True, exist_ok=True)
    idx.save(out_dir / "index.faiss", out_dir / "meta.json")
    logger.info("FAISS index saved (%d vectors) to %s", len(idx), out_dir)
    return idx


# ---------------------------------------------------------------------------
# Core gate
# ---------------------------------------------------------------------------

def check(
    question: dict[str, Any],
    *,
    index: Optional[DedupIndex] = None,
    db_path: Path = DEFAULT_DB,
    cap: int = DEFAULT_CAP,
    threshold: float = SIMILARITY_THRESHOLD,
) -> dict[str, Any]:
    """Run the FAISS dedup + concept-cap gate.

    A question fails if (a) it is a near-duplicate of an existing question
    (cosine > `threshold`) or (b) its (module, topic, difficulty) cell is at
    capacity `cap`.
    """
    text = str(question.get("question_text", "")).strip()
    if not text:
        return verdict(
            passed=False,
            score=0.0,
            reason="no question_text to dedup",
            issues=["empty question_text"],
            cost_usd=0.0,
            gate="dedup_check",
            max_similarity=0.0,
            nearest_id=None,
        )

    own_id = str(question.get("id") or "")
    idx = index if index is not None else _load_index(db_path)

    vec = embed(text)
    best_sim, nearest = idx.search(vec)
    # Never dedup against the question itself (re-checking an existing row).
    if nearest == own_id:
        best_sim = 0.0
        nearest = None

    if best_sim > threshold:
        return verdict(
            passed=False,
            score=0.0,
            reason=(f"near-duplicate of {nearest} (cosine {best_sim:.3f} > "
                    f"{threshold})"),
            issues=[f"nearest existing question {nearest}: {best_sim:.3f}"],
            cost_usd=0.0,
            gate="dedup_check",
            max_similarity=round(best_sim, 4),
            nearest_id=nearest,
        )

    # Concept-level cap.
    module, topic, difficulty = _question_cell(question)
    if module and topic and difficulty:
        cell_n = _cell_count(db_path, module, topic, difficulty)
        if cell_n >= cap:
            return verdict(
                passed=False,
                score=0.0,
                reason=(f"concept cap hit: {cell_n} generated questions already "
                        f"in ({module}, {topic}, {difficulty}) — cap {cap}"),
                issues=[f"cap {cap} reached for cell ({module},{topic},{difficulty})"],
                cost_usd=0.0,
                gate="dedup_check",
                max_similarity=round(best_sim, 4),
                nearest_id=nearest,
            )

    return verdict(
        passed=True,
        score=1.0,
        reason=(f"unique (nearest cosine {best_sim:.3f} ≤ {threshold})"
                + (f", cell ({module},{topic},{difficulty}) under cap" if module else "")),
        issues=[],
        cost_usd=0.0,
        gate="dedup_check",
        max_similarity=round(best_sim, 4),
        nearest_id=nearest,
    )


# ---------------------------------------------------------------------------
# Self-test (mocked embedder — no model download, no FAISS corpus needed)
# ---------------------------------------------------------------------------

def _run_self_test() -> int:
    """Exercise the verdict logic with a hand-built index and a fake embedder.

    Monkeypatches `embed` so deterministic vectors drive the cosine math.
    """
    import dedup_check as self_mod

    def fake_embed(text: str) -> np.ndarray:
        # Map a few tokens to orthogonal unit vectors for deterministic sims.
        table = {
            "force": np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
            "energy": np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32),
            "mitosis": np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32),
            "redox": np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
        }
        key = next((k for k in table if k in text.lower()), "other")
        v = table.get(key, np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32))
        return v / np.linalg.norm(v)

    original_embed = self_mod.embed
    original_dim = self_mod.EMBED_DIM
    self_mod.embed = fake_embed  # type: ignore
    self_mod.EMBED_DIM = 4
    try:
        # Build a tiny index by hand.
        idx = self_mod.DedupIndex()
        idx.EMBED_DIM = 4  # not used; IndexFlatIP created with current EMBED_DIM
        # Recreate the index at 4 dims for the test.
        import faiss
        idx.index = faiss.IndexFlatIP(4)
        idx.add("Q1", "What is the force on a 2 kg mass?", fake_embed("force"))
        idx.add("Q2", "How much energy is stored?", fake_embed("energy"))
        idx.add("Q3", "Describe mitosis.", fake_embed("mitosis"))

        cap_calls = {"n": 0}

        def fake_cell_count(db_path, module, topic, difficulty):
            cap_calls["n"] += 1
            # Pretend the (Physics, P1, Hard) cell is full.
            if module == "Physics" and topic == "P1" and difficulty == "Hard":
                return self_mod.DEFAULT_CAP
            return 0

        self_mod._cell_count = fake_cell_count  # type: ignore

        dup_q = {
            "id": "NEW1", "module": "Physics", "spec_topic": "P1", "difficulty": "Hard",
            "question_text": "Find the force on the block.",  # ~ "force"
        }
        unique_q = {
            "id": "NEW2", "module": "Chemistry", "spec_topic": "C2", "difficulty": "Easy",
            "question_text": "Balance this redox equation.",  # no token match → ~force vec
        }
        capfull_q = {
            "id": "NEW3", "module": "Physics", "spec_topic": "P1", "difficulty": "Hard",
            "question_text": "Balance this redox equation.",
        }

        r_dup = self_mod.check(dup_q, index=idx, db_path=Path("n/a"))
        r_cap = self_mod.check(capfull_q, index=idx, db_path=Path("n/a"))
        r_ok = self_mod.check(unique_q, index=idx, db_path=Path("n/a"))

        failures = 0
        for name, r, expect_pass in (
            ("duplicate_rejected", r_dup, False),
            ("cap_hit_rejected", r_cap, False),
            ("unique_accepted", r_ok, True),
        ):
            ok = r["pass"] == expect_pass
            flag = "PASS" if ok else "FAIL"
            print(f"  [{flag}] {name}: pass={r['pass']} sim={r['max_similarity']} "
                  f"({r['reason'][:60]})")
            if not ok:
                failures += 1
        print(f"\n{3 - failures}/3 cases passed")
        return failures
    finally:
        self_mod.embed = original_embed  # type: ignore
        self_mod.EMBED_DIM = original_dim


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_question(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "questions" in data and isinstance(data["questions"], list):
        return data["questions"][0]
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ESAT FAISS dedup gate (Layer 5)")
    p.add_argument("--question", type=Path, help="Path to a question JSON file")
    p.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to questions.db")
    p.add_argument("--build", action="store_true", help="Build the corpus FAISS index")
    p.add_argument("--cap", type=int, default=DEFAULT_CAP, help="Per-cell concept cap")
    p.add_argument("--self-test", action="store_true", help="Run the mocked self-test")
    args = p.parse_args(argv)

    if args.self_test:
        return _run_self_test()

    if args.build:
        build_index(db_path=args.db, out_dir=INDEX_DIR)
        return 0

    if not args.question:
        p.error("--question, --build, or --self-test is required")

    question = _load_question(args.question)
    idx = _load_index(args.db)
    result = check(question, index=idx, db_path=args.db, cap=args.cap)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
