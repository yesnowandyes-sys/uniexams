#!/usr/bin/env python3
"""
Per-topic pattern extraction for ESAT question generation.

Implements ESA-25 (research §10.2, ESA-17 plan §4.1):
  Stage 1  - Classify every corpus question to a topic-level spec_code
             (M1..M7, P1..P7, C1..C17, B1..B11) using GLM-5.2 (free).
  Stage 2+3 - For each topic with classified questions, a single extraction
             call produces three artefacts:
               - style_guide.<code>.md
               - distractor_catalogue.<code>.json
               - insight_scenarios.<code>.json

Outputs land under shared/patterns/<spec_code>/.

The model is whatever the gateway maps "claude-opus-4-8" / "claude-haiku-4-5"
to. On the z.ai gateway used by this Paperclip runtime, that resolves to
GLM-5.2 (free) / GLM-4.5-air respectively. Both are validated for
enrichment-style work (see shared/enriched-output/glm-trial/quality-audit.md).

Resume-aware: a per-question state file and per-topic state file make the
script safe to re-run; completed units are skipped. Use --reset to start
over.

Usage:
    python pattern-extraction.py --stage classify --limit 20 --dry-run
    python pattern-extraction.py --stage classify --concurrency 8
    python pattern-extraction.py --stage extract  --concurrency 3
    python pattern-extraction.py --stage all      --concurrency 6
    python pattern-extraction.py --reset

Env:
    ANTHROPIC_API_KEY   required for live calls
    ANTHROPIC_BASE_URL  gateway URL (z.ai or Anthropic)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import anthropic
except ImportError as e:  # pragma: no cover
    raise SystemExit(f"anthropic SDK missing: {e}. pip install -r scripts/requirements-enrichment.txt")

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPT_DIR.parent
DB_PATH = SHARED_DIR / "data" / "questions.db"
TAXONOMY_PATH = SHARED_DIR / "esat_taxonomy.json"
PATTERNS_DIR = SHARED_DIR / "patterns"
STATE_DIR = SHARED_DIR / "patterns" / "_state"

CLASSIFY_STATE_PATH = STATE_DIR / "classify.jsonl"
EXTRACT_STATE_PATH = STATE_DIR / "extract.jsonl"
RUN_LOG_PATH = STATE_DIR / "run_log.jsonl"

CLASSIFY_MODEL = "claude-haiku-4-5"   # cheap classifier; resolves via gateway
EXTRACT_MODEL = "claude-opus-4-8"    # deep extractor; resolves via gateway

# Pricing assumptions (USD / 1M tokens). On the z.ai gateway both models
# resolve to GLM-5.2 / GLM-4.5-air and are free for this account, so the
# only effect of these constants is a worst-case cost ceiling in the log.
CLASSIFY_PRICING = {"input": 0.80, "output": 4.00}   # Haiku list
EXTRACT_PRICING = {"input": 15.00, "output": 75.00}  # Opus list

MAX_RETRIES = 5
RETRY_BASE_DELAY = 2.5
REQUEST_TIMEOUT_SECONDS = 120
CLASSIFY_MAX_TOKENS = 400
EXTRACT_MAX_TOKENS = 8000

CLASSIFY_CONCURRENCY_DEFAULT = 8
EXTRACT_CONCURRENCY_DEFAULT = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("patterns")


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------

def load_taxonomy() -> dict[str, dict]:
    """Return flat map: topic_level_spec_code -> metadata.

    Topic-level codes are the second-level grouping in esat_taxonomy.json
    (e.g. M1=Units, M2=Number inside Mathematics 1; P1=Mechanics, etc.).
    These collide across modules (M1 means both "Mathematics 1 module" and
    "Units topic within Maths 1"), so we prefix with module code to make a
    globally unique topic_key: "MATHS1.M2", "PHYS.P1", "CHEM.C3", "BIO.B2".
    """
    t = json.load(open(TAXONOMY_PATH))
    out: dict[str, dict] = {}
    for m in t["modules"]:
        module_code = m["code"]
        module_name = m["name"]
        module_prefix = _module_prefix(module_code)
        for topic in m.get("topics", []):
            raw_code = topic.get("spec_code") or module_code
            # Build a globally-unique key like "MATHS1.M2"
            topic_key = f"{module_prefix}.{raw_code}"
            subtopics = topic.get("subtopics", [])
            skills_flat: list[str] = []
            for sub in subtopics:
                skills_flat.extend(sub.get("skills", []))
            out[topic_key] = {
                "topic_key": topic_key,
                "module_code": module_code,
                "module_name": module_name,
                "topic_code_raw": raw_code,
                "topic_name": topic.get("name", ""),
                "subtopic_count": len(subtopics),
                "subtopic_codes": [s.get("spec_code") for s in subtopics],
                "skills_sample": skills_flat[:8],
                "skills_total": len(skills_flat),
            }
    return out


def _module_prefix(module_code: str) -> str:
    """Stable short prefix per module."""
    return {
        "M1": "MATHS1",
        "M2": "MATHS2",
        "P": "PHYS",
        "C": "CHEM",
        "B": "BIO",
    }.get(module_code, module_code.upper())


# ---------------------------------------------------------------------------
# State (resume-aware)
# ---------------------------------------------------------------------------

STATE_LOCK = threading.Lock()


def _ensure_dirs():
    PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_classify_state() -> dict[str, dict]:
    """Return {question_id: classification_record} for completed entries."""
    if not CLASSIFY_STATE_PATH.exists():
        return {}
    out: dict[str, dict] = {}
    with CLASSIFY_STATE_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("status") == "success":
                out[rec["question_id"]] = rec
    return out


def append_classify(rec: dict):
    with STATE_LOCK, CLASSIFY_STATE_PATH.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def load_extract_state() -> set[str]:
    """Return set of topic_key values that completed successfully."""
    if not EXTRACT_STATE_PATH.exists():
        return set()
    out: set[str] = set()
    with EXTRACT_STATE_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("status") == "success":
                out.add(rec["topic_key"])
    return out


def append_extract(rec: dict):
    with STATE_LOCK, EXTRACT_STATE_PATH.open("a") as f:
        f.write(json.dumps(rec) + "\n")


# ---------------------------------------------------------------------------
# Anthropic client
# ---------------------------------------------------------------------------

_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=REQUEST_TIMEOUT_SECONDS)
    return _client


def call_with_retry(messages: list[dict], system: str, model: str, max_tokens: int) -> dict:
    """Return {text, input_tokens, output_tokens, attempts, error}."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = get_client().messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            text_parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
            return {
                "text": "".join(text_parts),
                "input_tokens": getattr(resp.usage, "input_tokens", 0),
                "output_tokens": getattr(resp.usage, "output_tokens", 0),
                "attempts": attempt,
                "error": None,
            }
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 0.7)
            log.warning("API call attempt %d failed: %s; sleeping %.1fs", attempt, last_err, delay)
            time.sleep(delay)
    return {
        "text": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "attempts": MAX_RETRIES,
        "error": last_err,
    }


# ---------------------------------------------------------------------------
# Stage 1: Classification
# ---------------------------------------------------------------------------

def _taxonomy_for_prompt(taxonomy: dict[str, dict]) -> dict[str, str]:
    """Build per-module compact taxonomy strings for the classifier prompt."""
    by_module: dict[str, list[dict]] = {}
    for tk, t in taxonomy.items():
        by_module.setdefault(t["module_code"], []).append(t)
    out: dict[str, str] = {}
    for mcode, topics in by_module.items():
        lines = []
        for t in topics:
            sub_list = ", ".join(t["subtopic_codes"])
            lines.append(
                f'  {t["topic_key"]} ({t["topic_code_raw"]}={t["topic_name"]}): '
                f'subtopics [{sub_list}]'
            )
        out[mcode] = "\n".join(lines)
    return out


def classify_one(question: dict, taxonomy_prompt: dict[str, str]) -> dict:
    """Classify a single question to a topic_key. Returns classification record."""
    qid = question["id"]
    qtext = (question.get("question_text") or "").strip()
    if not qtext:
        # Some rows store text only in metadata.raw_text
        try:
            meta = json.loads(question.get("metadata") or "{}")
            qtext = (meta.get("raw_text") or "").strip()
        except Exception:
            qtext = ""
    options = question.get("options") or ""
    if isinstance(options, str):
        try:
            options_obj = json.loads(options)
            opts_text = "\n".join(f"  {k}. {v}" for k, v in options_obj.items())
        except Exception:
            opts_text = options[:400]
    else:
        opts_text = str(options)[:400]

    # Pick module hint from row
    subj = (question.get("subject") or "").lower()
    mod = (question.get("module") or "").lower()
    if "bio" in subj or "bio" in mod:
        module_hint, allowed = "B", taxonomy_prompt.get("B", "")
    elif "chem" in subj or "chem" in mod:
        module_hint, allowed = "C", taxonomy_prompt.get("C", "")
    elif "phys" in subj or "phys" in mod:
        module_hint, allowed = "P", taxonomy_prompt.get("P", "")
    elif "maths" in mod or "math" in subj:
        # Could be M1 or M2 — pass both
        module_hint = "M"
        allowed = taxonomy_prompt.get("M1", "") + "\n" + taxonomy_prompt.get("M2", "")
    else:
        # ENGAA/NSAA/TMUA S1 mixes maths+physics — pass everything
        module_hint = "?"
        allowed = "\n".join(
            f"== {m} ==\n{taxonomy_prompt.get(m, '')}" for m in ("M1", "M2", "P", "C", "B")
        )

    system = (
        "You are an ESAT (Engineering and Natural Sciences Admissions Test) "
        "classification expert. You assign each question to exactly ONE topic_key "
        "from the provided ESAT Content Specification taxonomy.\n\n"
        "Topic_keys look like 'MATHS1.M2' (Number, inside Mathematics 1), "
        "'PHYS.P1' (Mechanics, inside Physics), 'CHEM.C3', 'BIO.B2', etc. "
        "Always choose the closest topic-level match. If a question genuinely "
        "spans two topics, pick the one that dominates the worked solution. "
        "If a question is off-syllabus (not in ESAT spec), return topic_key='OFF_SPEC'.\n\n"
        f"Module hint (subject detected from row): {module_hint}\n\n"
        f"Available topic_keys:\n{allowed}\n"
    )

    user = (
        f"Question ID: {qid}\n"
        f"Question text:\n{qtext[:1500]}\n\n"
        f"Options:\n{opts_text[:800]}\n\n"
        "Return ONLY a compact JSON object on one line:\n"
        '{"topic_key": "<one of the listed topic_keys or OFF_SPEC>", '
        '"confidence": <0-1>, "reason": "<=12 words>"}'
    )

    r = call_with_retry(
        messages=[{"role": "user", "content": user}],
        system=system,
        model=CLASSIFY_MODEL,
        max_tokens=CLASSIFY_MAX_TOKENS,
    )
    if r["error"]:
        return {
            "question_id": qid,
            "status": "error",
            "error": r["error"],
            "topic_key": None,
            "attempts": r["attempts"],
        }
    # Parse JSON from response
    text = r["text"].strip()
    # Tolerate code fences
    m = re.search(r"\{.*\}", text, re.DOTALL)
    payload = m.group(0) if m else text
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        # Last-ditch: extract topic_key via regex
        tk_match = re.search(r'"topic_key"\s*:\s*"([^"]+)"', text)
        parsed = {"topic_key": tk_match.group(1)} if tk_match else {"topic_key": "UNKNOWN"}
    topic_key = str(parsed.get("topic_key") or "UNKNOWN").upper().strip()
    return {
        "question_id": qid,
        "status": "success",
        "topic_key": topic_key,
        "confidence": parsed.get("confidence"),
        "reason": parsed.get("reason"),
        "input_tokens": r["input_tokens"],
        "output_tokens": r["output_tokens"],
        "attempts": r["attempts"],
    }


def fetch_all_questions() -> list[dict]:
    """Return every row from questions.db as a dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, exam_type, year, paper, module, section, subject, "
            "question_text, options, correct_answer, metadata FROM questions"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def stage_classify(args):
    _ensure_dirs()
    taxonomy = load_taxonomy()
    taxonomy_prompt = _taxonomy_for_prompt(taxonomy)
    done = load_classify_state()

    questions = fetch_all_questions()
    if args.limit:
        questions = questions[: args.limit]
    pending = [q for q in questions if q["id"] not in done]
    log.info(
        "Stage 1 classify: %d total, %d already done, %d pending",
        len(questions), len(done), len(pending),
    )
    if not pending:
        return

    if args.dry_run:
        for q in pending[:5]:
            log.info("DRY-RUN would classify %s", q["id"])
        return

    cost_acc = {"input": 0, "output": 0}
    cost_lock = threading.Lock()
    success = 0
    errors = 0
    t0 = time.time()

    def work(q):
        nonlocal success, errors
        rec = classify_one(q, taxonomy_prompt)
        append_classify(rec)
        with cost_lock:
            cost_acc["input"] += rec.get("input_tokens", 0)
            cost_acc["output"] += rec.get("output_tokens", 0)
            if rec.get("status") == "success":
                success += 1
            else:
                errors += 1
        return rec

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(work, q) for q in pending]
        for i, fut in enumerate(as_completed(futures), 1):
            _ = fut.result()
            if i % 25 == 0 or i == len(pending):
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed else 0
                eta = (len(pending) - i) / rate if rate else 0
                c = (
                    cost_acc["input"] * CLASSIFY_PRICING["input"] / 1_000_000
                    + cost_acc["output"] * CLASSIFY_PRICING["output"] / 1_000_000
                )
                log.info(
                    "Stage 1 progress %d/%d (%.1f/s, ETA %.0fs) ok=%d err=%d cost≈$%.4f",
                    i, len(pending), rate, eta, success, errors, c,
                )

    log.info(
        "Stage 1 complete: ok=%d err=%d input_tok=%d output_tok=%d in %.1fs",
        success, errors, cost_acc["input"], cost_acc["output"], time.time() - t0,
    )


# ---------------------------------------------------------------------------
# Stage 2+3: Per-topic extraction
# ---------------------------------------------------------------------------

# Group classification topic_keys by module for the extractor prompt context.
def _group_questions_by_topic(questions: list[dict], state: dict[str, dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for q in questions:
        rec = state.get(q["id"])
        if not rec or rec.get("status") != "success":
            continue
        tk = rec.get("topic_key") or "UNKNOWN"
        if tk in ("OFF_SPEC", "UNKNOWN", ""):
            continue
        out.setdefault(tk, []).append(q)
    return out


def _format_question_for_extraction(q: dict, idx: int) -> str:
    qtext = (q.get("question_text") or "").strip()
    if not qtext:
        try:
            meta = json.loads(q.get("metadata") or "{}")
            qtext = (meta.get("raw_text") or "").strip()
        except Exception:
            qtext = ""
    options = q.get("options") or ""
    if isinstance(options, str):
        try:
            obj = json.loads(options)
            opts_text = "\n    ".join(f"{k}. {v}" for k, v in obj.items())
        except Exception:
            opts_text = options[:400]
    else:
        opts_text = str(options)[:400]
    correct = q.get("correct_answer") or ""
    return (
        f"  Q{idx} [{q['id']}] source={q.get('exam_type')} {q.get('year')}:\n"
        f"    {qtext[:700]}\n"
        f"    Options:\n    {opts_text[:600]}\n"
        f"    Correct: {correct}\n"
    )


def extract_one(topic_key: str, questions: list[dict], topic_meta: dict) -> dict:
    """One per-topic extraction call -> 3 artefact files."""
    out_dir = PATTERNS_DIR / topic_key
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_block = "\n".join(
        _format_question_for_extraction(q, i + 1) for i, q in enumerate(questions[:60])
    )

    skills_list = ", ".join(topic_meta.get("skills_sample", [])) or "n/a"

    system = (
        "You are an expert assessment analyst specialising in Cambridge "
        "admissions tests (ENGAA, NSAA, ESAT). You have deep knowledge of "
        "A-Level Mathematics, Physics, Chemistry, and Biology curricula.\n\n"
        f"You are analysing questions for ONE ESAT spec topic: {topic_key} "
        f"({topic_meta.get('topic_name','?')} inside {topic_meta.get('module_name','?')}).\n\n"
        "Your task is to analyse the provided corpus of past-paper questions and "
        "produce THREE artefacts for this topic:\n"
        "  1. DISTRACTOR_CATALOGUE — categorised distractor types with examples "
        "and generation strategies\n"
        "  2. STYLE_GUIDE — question structure patterns, difficulty calibration, "
        "wording conventions, calculator-free arithmetic patterns\n"
        "  3. INSIGHT_SCENARIOS — 3-5 'Aha!' scenarios requiring deep conceptual "
        "understanding of this topic\n\n"
        "Be specific, quantitative, and evidence-based. Quote example questions "
        "where helpful. Do not speculate — only report patterns observable in "
        "the provided corpus. If the corpus for this topic is thin (<5 questions), "
        "produce best-effort patterns grounded in the ESAT Content Spec skills list "
        "and flag the artefact with corpus_backed=false.\n\n"
        "Output structure (use exactly these section markers):\n\n"
        "<<<DISTRACTORS>>>\n<valid JSON array>\n<<<STYLE>>>\n<markdown>\n"
        "<<<SCENARIOS>>>\n<valid JSON array>\n"
    )

    user = (
        f"ESAT Content Specification — Topic {topic_key} "
        f"({topic_meta.get('topic_name','?')})\n"
        f"Module: {topic_meta.get('module_name','?')} ({topic_meta.get('module_code','?')})\n"
        f"Subtopic codes: {', '.join(topic_meta.get('subtopic_codes', []) or [])}\n"
        f"Spec skills sample: {skills_list}\n\n"
        f"Classified corpus questions ({len(questions)} total, showing up to 60):\n\n"
        f"{corpus_block}\n\n"
        "Now produce DISTRACTOR_CATALOGUE, STYLE_GUIDE, INSIGHT_SCENARIOS using "
        "the section markers above. For DISTRACTORS, each entry should have: "
        "distractor_type, frequency (count or 'rare'), example_question_id, "
        "why_effective, generation_strategy. For SCENARIOS, each entry should "
        "have: scenario_description, key_insight, discrimination_factors "
        "(list), difficulty_band (1-3|4-6|7-9)."
    )

    r = call_with_retry(
        messages=[{"role": "user", "content": user}],
        system=system,
        model=EXTRACT_MODEL,
        max_tokens=EXTRACT_MAX_TOKENS,
    )
    rec: dict[str, Any] = {
        "topic_key": topic_key,
        "question_count": len(questions),
        "input_tokens": r["input_tokens"],
        "output_tokens": r["output_tokens"],
        "attempts": r["attempts"],
    }
    if r["error"]:
        rec["status"] = "error"
        rec["error"] = r["error"]
        append_extract(rec)
        return rec

    text = r["text"]
    # Split using the markers
    def _slice(marker_a: str, marker_b: str) -> str:
        i = text.find(marker_a)
        if i < 0:
            return ""
        start = i + len(marker_a)
        j = text.find(marker_b, start) if marker_b else -1
        return text[start : j if j >= 0 else None].strip()

    distractors_raw = _slice("<<<DISTRACTORS>>>", "<<<STYLE>>>")
    style_raw = _slice("<<<STYLE>>>", "<<<SCENARIOS>>>")
    scenarios_raw = _slice("<<<SCENARIOS>>>", "")

    # Parse JSON arrays (tolerant: find first [ to last ])
    def _parse_json_array(s: str):
        s = s.strip()
        # strip code fences
        s = re.sub(r"^```[a-zA-Z]*\n", "", s)
        s = re.sub(r"\n```\s*$", "", s)
        i, j = s.find("["), s.rfind("]")
        if i < 0 or j < 0 or j < i:
            return None
        try:
            return json.loads(s[i : j + 1])
        except json.JSONDecodeError:
            return None

    distractors = _parse_json_array(distractors_raw)
    scenarios = _parse_json_array(scenarios_raw)

    # Persist artefacts
    (out_dir / f"distractor_catalogue.{topic_key}.json").write_text(
        json.dumps(
            {
                "topic_key": topic_key,
                "topic_name": topic_meta.get("topic_name"),
                "module_code": topic_meta.get("module_code"),
                "corpus_question_count": len(questions),
                "corpus_backed": len(questions) >= 5,
                "distractors": distractors if distractors is not None else [],
                "_raw": distractors_raw if distractors is None else None,
            },
            indent=2,
        )
    )
    (out_dir / f"style_guide.{topic_key}.md").write_text(
        f"# Style Guide — {topic_key} ({topic_meta.get('topic_name','?')})\n\n"
        f"- Module: {topic_meta.get('module_name','?')} ({topic_meta.get('module_code','?')})\n"
        f"- Corpus questions classified under this topic: {len(questions)}\n"
        f"- corpus_backed: {len(questions) >= 5}\n\n"
        f"---\n\n{style_raw or '_No style output extracted._'}\n"
    )
    (out_dir / f"insight_scenarios.{topic_key}.json").write_text(
        json.dumps(
            {
                "topic_key": topic_key,
                "topic_name": topic_meta.get("topic_name"),
                "module_code": topic_meta.get("module_code"),
                "corpus_question_count": len(questions),
                "corpus_backed": len(questions) >= 5,
                "scenarios": scenarios if scenarios is not None else [],
                "_raw": scenarios_raw if scenarios is None else None,
            },
            indent=2,
        )
    )

    rec["status"] = "success"
    rec["distractors_parsed"] = distractors is not None
    rec["scenarios_parsed"] = scenarios is not None
    rec["style_chars"] = len(style_raw)
    append_extract(rec)
    return rec


def stage_extract(args):
    _ensure_dirs()
    taxonomy = load_taxonomy()
    state = load_classify_state()
    questions = fetch_all_questions()
    groups = _group_questions_by_topic(questions, state)
    done = load_extract_state()

    log.info(
        "Stage 2+3 extract: %d topic groups from classified corpus, %d already extracted",
        len(groups), len(done),
    )
    # Sort by group size (largest first) so we get the highest-signal topics done first
    pending = sorted(
        ((tk, qs) for tk, qs in groups.items() if tk not in done and tk in taxonomy),
        key=lambda kv: -len(kv[1]),
    )
    log.info("Pending topics (taxonomy-backed, sorted by corpus size): %d", len(pending))
    if args.limit:
        pending = pending[: args.limit]
    if args.dry_run:
        for tk, qs in pending[:10]:
            log.info("DRY-RUN would extract %s (%d questions)", tk, len(qs))
        return

    cost_acc = {"input": 0, "output": 0}
    cost_lock = threading.Lock()
    success = 0
    errors = 0
    t0 = time.time()

    def work(tk_qs):
        nonlocal success, errors
        tk, qs = tk_qs
        meta = taxonomy.get(tk, {})
        rec = extract_one(tk, qs, meta)
        with cost_lock:
            cost_acc["input"] += rec.get("input_tokens", 0)
            cost_acc["output"] += rec.get("output_tokens", 0)
            if rec.get("status") == "success":
                success += 1
            else:
                errors += 1
        return rec

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(work, item) for item in pending]
        for i, fut in enumerate(as_completed(futures), 1):
            _ = fut.result()
            if i % 5 == 0 or i == len(pending):
                elapsed = time.time() - t0
                c = (
                    cost_acc["input"] * EXTRACT_PRICING["input"] / 1_000_000
                    + cost_acc["output"] * EXTRACT_PRICING["output"] / 1_000_000
                )
                log.info(
                    "Stage 2+3 progress %d/%d ok=%d err=%d cost≈$%.4f",
                    i, len(pending), success, errors, c,
                )

    log.info(
        "Stage 2+3 complete: ok=%d err=%d input_tok=%d output_tok=%d in %.1fs",
        success, errors, cost_acc["input"], cost_acc["output"], time.time() - t0,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--stage",
        choices=("classify", "extract", "all"),
        default="all",
        help="Which stage to run.",
    )
    p.add_argument("--concurrency", type=int, default=None, help="Override worker count.")
    p.add_argument("--limit", type=int, default=None, help="Cap units processed (debug).")
    p.add_argument("--dry-run", action="store_true", help="No API calls; print plan.")
    p.add_argument("--reset", action="store_true", help="Delete state files and exit.")
    args = p.parse_args()

    if args.reset:
        for f in (CLASSIFY_STATE_PATH, EXTRACT_STATE_PATH, RUN_LOG_PATH):
            if f.exists():
                log.warning("removing %s", f)
                f.unlink()
        return

    if args.concurrency is None:
        args.concurrency = (
            CLASSIFY_CONCURRENCY_DEFAULT if args.stage == "classify"
            else EXTRACT_CONCURRENCY_DEFAULT if args.stage == "extract"
            else min(CLASSIFY_CONCURRENCY_DEFAULT, EXTRACT_CONCURRENCY_DEFAULT)
        )

    log.info(
        "pattern-extraction starting: stage=%s concurrency=%d limit=%s dry_run=%s",
        args.stage, args.concurrency, args.limit, args.dry_run,
    )

    if args.stage in ("classify", "all"):
        stage_classify(args)
    if args.stage in ("extract", "all"):
        stage_extract(args)


if __name__ == "__main__":
    main()
