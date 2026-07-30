#!/usr/bin/env python3
"""
Review unverified questions using GLM-4.7-Flash (free tier).
Outputs a JSON report with human-readable issue descriptions for each question.
Does NOT modify the database.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import openai

SCRIPTS_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPTS_DIR.parent
DB_PATH = SHARED_DIR / "data" / "questions.db"

# z.ai API (free tier for glm-4.7-flash)
ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
DEFAULT_MODEL = "glm-4.7-flash"

INTER_CALL_DELAY_S = 1.0
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0


def get_api_key():
    # Try env vars first
    key = os.environ.get("ZAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    # Fall back to z.ai plugin catalog
    for candidate in [
        Path.home() / ".openclaw" / "agents" / "esat-manager" / "agent" / "plugins" / "zai" / "catalog.json",
    ]:
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text())
                key = data.get("providers", {}).get("zai", {}).get("apiKey")
                if key:
                    return key
            except Exception:
                pass
    print("ERROR: No API key found. Set ZAI_API_KEY or ANTHROPIC_API_KEY.", file=sys.stderr)
    sys.exit(1)


def fetch_unverified(db):
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT id, exam_type, year, paper, module, section, subject,
               question_number, question_text, options, correct_answer,
               enrichment, question_images
        FROM questions
        WHERE json_extract(enrichment, '$.verification.verified') = 0
          AND json_extract(enrichment, '$.verification.issues') IS NOT NULL
        ORDER BY exam_type, year, question_number
        """
    )
    return [dict(r) for r in rows.fetchall()]


def build_review_prompt(question):
    enrichment = json.loads(question["enrichment"]) if question["enrichment"] else {}
    issues = enrichment.get("verification", {}).get("issues", [])
    markdown = enrichment.get("markdown", "")

    prompt = f"""You are reviewing an ESAT-style exam question that has enrichment data with issues flagged by a previous verification pass.

## Question
**ID:** {question['id']}
**Exam:** {question['exam_type']} {question['year']} Paper {question['paper'] or '?'} Section {question['section'] or '?'} Q{question['question_number']}
**Module:** {question['module'] or '?'} | **Subject:** {question['subject'] or '?'}

### Question Text:
{question['question_text']}

### Options:
{question['options']}

### Stated Correct Answer: {question['correct_answer']}

### Current Enrichment (markdown explanation):
{markdown if markdown else '(no explanation)'}

## Verification Issues Previously Flagged:
{json.dumps(issues, indent=2)}

## Your Task
Look at the question carefully. For EACH issue listed above, explain in plain English:
1. What exactly is wrong
2. What the correct value/fix should be
3. Whether this is something that can be fixed by correcting the enrichment data, or whether the underlying question extraction itself is broken (bad OCR, missing text, garbled formulas)

Be specific and concise. Use the correct mathematical notation when referencing formulas.

## Output Format
Return a JSON object:
{{
  "question_id": "{question['id']}",
  "total_issues": <number>,
  "issues": [
    {{
      "original_flag": "<the verification issue text>",
      "plain_english": "<what's actually wrong>",
      "fix_type": "enrichment_correction" | "data_extraction_problem" | "answer_mismatch" | "formatting_fix" | "requires_manual_review",
      "suggested_fix": "<specific suggestion if applicable>"
    }}
  ],
  "overall_assessment": "<1-2 sentence summary>"
}}"""

    return prompt


def call_model(client, model, prompt):
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.1,
            )
            return resp.choices[0].message.content, resp.usage
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"    API error (attempt {attempt+1}/{MAX_RETRIES}): {e}. Retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)
            else:
                raise


def extract_json(text):
    """Extract JSON from response, handling markdown code blocks."""
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return json.loads(text[start:end].strip())
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return json.loads(text[start:end].strip())
    # Last resort: find first { to last }
    start = text.index("{")
    end = text.rindex("}") + 1
    return json.loads(text[start:end])


def main():
    parser = argparse.ArgumentParser(description="Review unverified questions with GLM-4.7-Flash")
    parser.add_argument("--limit", type=int, default=None, help="Max questions to process")
    parser.add_argument("--output", type=str, default=str(SHARED_DIR / "data" / "unverified-review.json"), help="Output JSON file")
    args = parser.parse_args()

    api_key = get_api_key()
    client = openai.OpenAI(api_key=api_key, base_url=ZAI_BASE_URL)

    db = sqlite3.connect(DB_PATH)
    questions = fetch_unverified(db)
    print(f"Found {len(questions)} unverified questions to review", file=sys.stderr)
    if args.limit:
        questions = questions[:args.limit]
        print(f"Limited to {args.limit} questions", file=sys.stderr)

    results = []
    total_input_tokens = 0
    total_output_tokens = 0

    for i, q in enumerate(questions, 1):
        qid = q["id"]
        print(f"[{i}/{len(questions)}] Reviewing {qid}...", file=sys.stderr)

        prompt = build_review_prompt(q)
        try:
            response_text, usage = call_model(client, DEFAULT_MODEL, prompt)
            review = extract_json(response_text)
            review["raw_response"] = response_text
            review["tokens"] = {"input": usage.prompt_tokens, "output": usage.completion_tokens}
            total_input_tokens += usage.prompt_tokens
            total_output_tokens += usage.completion_tokens
            results.append(review)
            print(f"  → {review.get('total_issues', '?')} issues assessed", file=sys.stderr)
        except Exception as e:
            print(f"  → FAILED: {e}", file=sys.stderr)
            results.append({
                "question_id": qid,
                "error": str(e),
                "tokens": None,
            })

        time.sleep(INTER_CALL_DELAY_S)

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": DEFAULT_MODEL,
        "total_questions": len(questions),
        "total_issues_assessed": sum(len(r.get("issues", [])) for r in results if "error" not in r),
        "total_tokens": {"input": total_input_tokens, "output": total_output_tokens},
        "results": results,
    }
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport saved to {output_path}", file=sys.stderr)
    print(f"Total tokens: {total_input_tokens} in / {total_output_tokens} out", file=sys.stderr)
    print(f"Questions reviewed: {len(results)}", file=sys.stderr)
    print(f"Errors: {sum(1 for r in results if 'error' in r)}", file=sys.stderr)

    db.close()


if __name__ == "__main__":
    main()
