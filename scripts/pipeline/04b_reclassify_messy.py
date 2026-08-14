#!/usr/bin/env python3
"""Phase 4b: LLM re-classification for questions with missing/messy
topic_classification (empty modules_json, or module_code that doesn't match
a recognized taxonomy token after cleaning).

Batches 10 questions per GLM-4.7 call. Writes results back into the
enrichment JSON's topic_classification (and difficulty fields if missing),
so Phase 2's extraction logic can be re-run afterward to populate
modules_json / topic_keys_json / question_type / difficulty as usual.

Resumable via pipeline_progress (phase='04b-reclassify'), keyed by a batch id.
"""
import json
import re

from db import ensure_pipeline_progress_table, get_conn, get_progress_status, mark_progress
from llm import call_glm, extract_json
from taxonomy import condensed_summary, extract_module_codes, is_valid_spec_code

PHASE = "04b-reclassify"
BATCH_SIZE = 10

VALID_MODULE_TOKEN_RE = re.compile(
    r"^(MM[1-8]|M[1-7]|P[1-7]|B(1[01]|[1-9])|C(1[0-7]|[1-9])|M1|M2|P|C|B|OUT_OF_SPEC)$"
)

PROMPT_HEADER = """You are an expert at classifying UK university entrance exam questions
(ENGAA, NSAA, TMUA, ESAT — Cambridge admissions tests) against the ESAT taxonomy.

## ESAT Taxonomy (module: topic spec_code — name: [subtopic spec_codes])
{taxonomy_summary}

## Instructions
For each question below, classify it against the taxonomy above.
- module_code: one of M1, M2, P, C, B (the top-level taxonomy module)
- topic_code: the topic-level spec_code (e.g. M4, P3, MM1, B4, C4) from the taxonomy
- content_code: the finest-grain spec_code (e.g. M4.16, P3.7) — your best guess at the specific skill
- If the question is out-of-spec (predates ESAT, no reasonable mapping), use module_code "OUT_OF_SPEC"
  and set is_out_of_spec true.
- difficulty_rating: integer 1-10; difficulty_category: Easy/Medium/Hard

## Questions
{questions_block}

Respond with ONLY a JSON array (no markdown fences, no preamble), one object per question, in the
same order, each shaped exactly like:
{{"id": "<question id>", "module": "<full module name>", "module_code": "M1", "topic_code": "M4",
  "topic_name": "<topic name>", "content_code": "M4.16", "question_type": "<short label>",
  "is_out_of_spec": false, "difficulty_rating": 5, "difficulty_category": "Medium"}}
"""


def find_targets(conn) -> list:
    rows = conn.execute("SELECT * FROM questions").fetchall()
    targets = []
    for row in rows:
        mj = json.loads(row["modules_json"] or "[]")
        if not mj:
            targets.append(row)
            continue
        if any(not VALID_MODULE_TOKEN_RE.match(tok.strip()) for tok in mj):
            targets.append(row)
    return targets


def build_batch_prompt(batch: list) -> str:
    blocks = []
    for q in batch:
        blocks.append(
            f"### {q['id']}\n"
            f"Exam: {q['exam_type']} ({q['year'] or ''})\n"
            f"Text: {q['question_text']}\n"
            f"Options: {q['options']}\n"
            f"Correct answer: {q['correct_answer']}"
        )
    return PROMPT_HEADER.format(
        taxonomy_summary=condensed_summary(), questions_block="\n\n".join(blocks)
    )


def apply_classification(conn, qid: str, cls: dict):
    row = conn.execute("SELECT enrichment FROM questions WHERE id = ?", (qid,)).fetchone()
    enrichment = json.loads(row["enrichment"] or "{}")
    enrichment["topic_classification"] = {
        "module": cls.get("module", ""),
        "module_code": cls.get("module_code", ""),
        "topic_code": cls.get("topic_code", ""),
        "topic_name": cls.get("topic_name", ""),
        "content_code": cls.get("content_code", ""),
        "question_type": cls.get("question_type", ""),
        "is_out_of_spec": bool(cls.get("is_out_of_spec", False)),
    }
    if enrichment.get("difficulty_rating") is None and cls.get("difficulty_rating") is not None:
        enrichment["difficulty_rating"] = cls.get("difficulty_rating")
    if not enrichment.get("difficulty_category") and cls.get("difficulty_category"):
        enrichment["difficulty_category"] = cls.get("difficulty_category")
    enrichment["reclassified_at"] = enrichment.get("reclassified_at") or True
    conn.execute("UPDATE questions SET enrichment = ? WHERE id = ?", (json.dumps(enrichment), qid))


def main():
    conn = get_conn()
    ensure_pipeline_progress_table(conn)

    targets = find_targets(conn)
    print(f"Phase 4b: {len(targets)} questions need re-classification")

    batches = [targets[i : i + BATCH_SIZE] for i in range(0, len(targets), BATCH_SIZE)]
    done = 0
    for bi, batch in enumerate(batches):
        batch_key = f"batch-{bi}"
        if get_progress_status(conn, PHASE, batch_key) == "done":
            done += len(batch)
            continue

        mark_progress(conn, PHASE, batch_key, "processing")
        prompt = build_batch_prompt(batch)
        raw = call_glm(prompt, model="glm-4.7", max_tokens=6000, temperature=0.1)
        if not raw:
            mark_progress(conn, PHASE, batch_key, "error", result="no response")
            print(f"  batch {bi}: FAILED (no response)")
            continue

        parsed = extract_json(raw)
        if not isinstance(parsed, list):
            mark_progress(conn, PHASE, batch_key, "error", result="bad JSON shape")
            print(f"  batch {bi}: FAILED (bad JSON shape: {type(parsed)})")
            continue

        by_id = {item.get("id"): item for item in parsed if isinstance(item, dict)}
        applied = 0
        for q in batch:
            cls = by_id.get(q["id"])
            if not cls:
                continue
            apply_classification(conn, q["id"], cls)
            applied += 1
        conn.commit()
        mark_progress(conn, PHASE, batch_key, "done", result=f"{applied}/{len(batch)} applied")
        done += applied
        print(f"  batch {bi}: {applied}/{len(batch)} classified ({done}/{len(targets)} total)")

    conn.close()
    print(f"Phase 4b complete: {done}/{len(targets)} re-classified")


if __name__ == "__main__":
    main()
