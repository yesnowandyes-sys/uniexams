#!/usr/bin/env python3
"""Phase 5: Assign ESAT taxonomy skills (spec_codes) to every question.

Two-phase mapping (proposal Section 6.2):
  5a. Programmatic: enrichment.topic_classification.content_code, cleaned via
      taxonomy.extract_spec_codes(), already IS a valid spec_code for most
      questions -> no LLM needed.
  5b. LLM (GLM-4.7, batched 10/call): everything left over -- content_code
      missing/messy/out-of-spec, or genuinely multi-skill questions.

Idempotent: only targets rows where skills_json is still '[]'.
Resumable via pipeline_progress (phase='05-skills'), keyed by batch id for
LLM batches and 'programmatic' for the bulk pass.
"""
import json
import re

from db import ensure_pipeline_progress_table, get_conn, get_progress_status, mark_progress
from llm import call_glm, extract_json
from taxonomy import condensed_summary, extract_spec_codes, is_valid_spec_code

PHASE = "05-skills"
BATCH_SIZE = 10

SKILLS_PROMPT_HEADER = """You are an expert at mapping UK university entrance exam questions
(ENGAA, NSAA, TMUA, ESAT -- Cambridge admissions tests) to the ESAT taxonomy's finest-grain skills.

## ESAT Taxonomy (module: topic spec_code -- name: [skill spec_codes])
{taxonomy_summary}

## Instructions
For each question below, identify which taxonomy skill spec_codes (the ones in brackets, e.g.
M2.7, P1.2, MM1.3, B4.2, C4.6) it tests. A question may test 1-3 skills, ordered by relevance.
If the question genuinely doesn't map to the ESAT spec (predates it, no reasonable equivalent),
return ["OUT_OF_SPEC"] for that question.

## Questions
{questions_block}

Respond with ONLY a JSON array (no markdown fences, no preamble), one object per question, in the
same order, each shaped exactly like:
{{"id": "<question id>", "skills": ["M2.7", "M3.1"]}}
"""


def find_targets(conn) -> list:
    return conn.execute("SELECT * FROM questions WHERE skills_json = '[]'").fetchall()


def programmatic_pass(conn, rows) -> list:
    """Phase 5a: direct content_code -> spec_code mapping. Returns leftover rows."""
    leftover = []
    mapped = 0
    for row in rows:
        enrichment = json.loads(row["enrichment"] or "{}")
        tc = enrichment.get("topic_classification") or {}
        content_code = tc.get("content_code", "") or ""

        if tc.get("is_out_of_spec") or content_code.strip().upper() in ("OUT_OF_SPEC", "N/A", ""):
            if not content_code or content_code.strip().upper() in ("N/A", ""):
                if not tc.get("is_out_of_spec"):
                    leftover.append(row)
                    continue
            conn.execute(
                "UPDATE questions SET skills_json = ? WHERE id = ?",
                (json.dumps(["OUT_OF_SPEC"]), row["id"]),
            )
            mapped += 1
            continue

        codes = extract_spec_codes(content_code)
        codes = [c for c in codes if is_valid_spec_code(c)]
        if codes:
            conn.execute(
                "UPDATE questions SET skills_json = ? WHERE id = ?",
                (json.dumps(codes), row["id"]),
            )
            mapped += 1
        else:
            leftover.append(row)

    conn.commit()
    print(f"Phase 5a (programmatic): {mapped} mapped, {len(leftover)} left for LLM")
    return leftover


def build_batch_prompt(batch: list) -> str:
    blocks = []
    for q in batch:
        blocks.append(
            f"### {q['id']}\n"
            f"Exam: {q['exam_type']} ({q['year'] or ''})\n"
            f"Text: {q['question_text']}\n"
            f"Options: {q['options']}"
        )
    return SKILLS_PROMPT_HEADER.format(
        taxonomy_summary=condensed_summary(), questions_block="\n\n".join(blocks)
    )


def llm_pass(conn, targets):
    batches = [targets[i : i + BATCH_SIZE] for i in range(0, len(targets), BATCH_SIZE)]
    done = 0
    for bi, batch in enumerate(batches):
        batch_key = f"batch-{bi}"
        if get_progress_status(conn, PHASE, batch_key) == "done":
            done += len(batch)
            continue

        mark_progress(conn, PHASE, batch_key, "processing")
        prompt = build_batch_prompt(batch)
        raw = call_glm(prompt, model="glm-4.7", max_tokens=4096, temperature=0.1)
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
            item = by_id.get(q["id"])
            if not item:
                continue
            skills = item.get("skills") or []
            skills = [s for s in skills if s == "OUT_OF_SPEC" or is_valid_spec_code(s)]
            if not skills:
                skills = ["OUT_OF_SPEC"]
            conn.execute(
                "UPDATE questions SET skills_json = ? WHERE id = ?",
                (json.dumps(skills), q["id"]),
            )
            applied += 1
        conn.commit()
        mark_progress(conn, PHASE, batch_key, "done", result=f"{applied}/{len(batch)} applied")
        done += applied
        print(f"  batch {bi}: {applied}/{len(batch)} skills-assigned ({done}/{len(targets)} total)")

    print(f"Phase 5b complete: {done}/{len(targets)} LLM-assigned")


def main():
    conn = get_conn()
    ensure_pipeline_progress_table(conn)

    rows = find_targets(conn)
    print(f"Phase 5: {len(rows)} questions need skills_json")

    if get_progress_status(conn, PHASE, "programmatic") == "done":
        leftover = conn.execute("SELECT * FROM questions WHERE skills_json = '[]'").fetchall()
        print(f"Phase 5a already done, {len(leftover)} left for LLM")
    else:
        leftover = programmatic_pass(conn, rows)
        mark_progress(conn, PHASE, "programmatic", "done")

    llm_pass(conn, leftover)

    total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    empty = conn.execute("SELECT COUNT(*) FROM questions WHERE skills_json = '[]'").fetchone()[0]
    print(f"\nFinal: skills_json populated {total - empty}/{total}")
    conn.close()


if __name__ == "__main__":
    main()
