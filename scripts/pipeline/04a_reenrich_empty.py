#!/usr/bin/env python3
"""Phase 4a: Full re-enrichment for questions with empty enrichment markdown.

Uses GLM-5.2 (z.ai) to generate a worked solution, distractor analysis,
classification, difficulty rating, and OCR-correction check, in the same
markdown + JSON shape as the existing enrichment records so Phase 2's
extraction code works on the result unchanged.

Resumable via pipeline_progress (phase='04a-reenrich').
"""
import json
import re
import sys
from datetime import datetime, timezone

from db import ensure_pipeline_progress_table, get_conn, get_progress_status, mark_progress
from llm import call_glm, extract_json

PHASE = "04a-reenrich"

PROMPT_TEMPLATE = """You are an expert tutor for UK university admissions tests (ENGAA, NSAA, TMUA, ESAT — Cambridge admissions tests).

Given the question below, produce a full enrichment record.

## Question
ID: {qid}
Exam: {exam_type} ({year})
Text: {question_text}
Options: {options}
Correct answer: {correct_answer}

Respond with ONLY a single JSON object (no markdown fences, no preamble) with this exact shape:
{{
  "markdown": "<the full markdown below, as one string with \\n newlines>",
  "difficulty_rating": <integer 1-10>,
  "difficulty_category": "<Easy|Medium|Hard>",
  "topic_classification": {{
    "module": "<full module name, e.g. Mathematics 1>",
    "module_code": "<one of: M1, M2, P, C, B — or a topic-level code like M4, P3, MM1, B4, C4>",
    "topic_code": "<topic-level code, e.g. M4, P3, MM1, B4, C4>",
    "topic_name": "<topic name>",
    "content_code": "<finest-grain spec code, e.g. M4.16, P3.7 — best guess>",
    "question_type": "<short label, e.g. 'Multi-step calculation'>",
    "is_out_of_spec": <true|false>
  }},
  "ocr_corrections": []
}}

The "markdown" field must contain exactly these sections, in this order, using "## " headers:

## Worked Solution
(numbered steps, using $inline math$ and $$display math$$ throughout)

## Distractor Analysis
- **A (expr):** why a student might pick this wrong answer
- **B (expr):** ...
(one bullet per option, explaining why it's wrong; skip the correct option)

## Classification
- **Module:** ...
- **Module Code:** ...
- **Topic Code:** ...
- **Topic Name:** ...
- **Content Code:** ...
- **Question Type:** ...

## Difficulty Rating
Difficulty: N/10
Difficulty Category: Easy|Medium|Hard

## OCR Corrections
No OCR corrections needed.

## Diagram Descriptions
No diagrams needed.

The markdown must end with a line: "The correct answer is **{correct_answer}**."
"""


def build_prompt(q) -> str:
    return PROMPT_TEMPLATE.format(
        qid=q["id"],
        exam_type=q["exam_type"],
        year=q["year"] or "",
        question_text=q["question_text"],
        options=q["options"],
        correct_answer=q["correct_answer"],
    )


def main():
    conn = get_conn()
    ensure_pipeline_progress_table(conn)

    rows = conn.execute("SELECT * FROM questions").fetchall()
    targets = []
    for row in rows:
        e = json.loads(row["enrichment"] or "{}")
        if not (e.get("markdown") or "").strip():
            targets.append(row)

    print(f"Phase 4a: {len(targets)} questions need full re-enrichment")

    done = 0
    for q in targets:
        if get_progress_status(conn, PHASE, q["id"]) == "done":
            done += 1
            continue

        mark_progress(conn, PHASE, q["id"], "processing")
        prompt = build_prompt(q)
        # glm-5.2 is a reasoning model — reasoning_content alone often runs
        # 10-15k tokens before it emits the final answer, so max_tokens must
        # be generous or the call gets cut off (finish_reason='length', empty
        # content). 20000 leaves headroom for both.
        raw = call_glm(prompt, model="glm-5.2", max_tokens=20000, temperature=0.2)
        if not raw:
            mark_progress(conn, PHASE, q["id"], "error", result="no response from GLM")
            print(f"  {q['id']}: FAILED (no response)")
            continue

        parsed = extract_json(raw)
        if not parsed or not parsed.get("markdown"):
            mark_progress(conn, PHASE, q["id"], "error", result="failed to parse JSON")
            print(f"  {q['id']}: FAILED (bad JSON)")
            continue

        enrichment = {
            "status": "success",
            "model": "glm-5.2",
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            "markdown": parsed.get("markdown", ""),
            "difficulty_rating": parsed.get("difficulty_rating"),
            "difficulty_category": parsed.get("difficulty_category"),
            "topic_classification": parsed.get("topic_classification", {}),
            "ocr_corrections": parsed.get("ocr_corrections", []),
            "error": None,
            "processor_id": "pipeline-04a-reenrich",
            "backfilled_at": datetime.now(timezone.utc).isoformat(),
        }
        conn.execute(
            "UPDATE questions SET enrichment = ? WHERE id = ?",
            (json.dumps(enrichment), q["id"]),
        )
        conn.commit()
        mark_progress(conn, PHASE, q["id"], "done")
        done += 1
        print(f"  {q['id']}: done ({done}/{len(targets)})")

    conn.close()
    print(f"Phase 4a complete: {done}/{len(targets)} re-enriched")


if __name__ == "__main__":
    main()
