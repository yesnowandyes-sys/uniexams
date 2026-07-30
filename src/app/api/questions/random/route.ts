import { NextRequest, NextResponse } from "next/server";
import { queryQuestions, countQuestions, type QuestionFilters } from "@/lib/db";

/**
 * GET /api/questions/random
 *
 * Returns one or more random questions.
 * Same filters as /api/questions (exam_type, year, module, subject, section,
 * difficulty, topic, enriched_only).
 *
 * Query params:
 *   count     - number of random questions (default 1, max 20)
 *   reveal    - include correct_answer + explanation (default false)
 */
export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const count = Math.min(parseInt(sp.get("count") ?? "1", 10) || 1, 20);
  const reveal = sp.get("reveal") === "true";

  const filters: QuestionFilters = {
    limit: count,
    random: true,
    verified_only: sp.get("include_unverified") !== "true",
  };

  const exam_type = sp.get("exam_type");
  if (exam_type) filters.exam_type = exam_type;
  const year = sp.get("year");
  if (year) filters.year = year;
  const module = sp.get("module");
  if (module) filters.module = module;
  const subject = sp.get("subject");
  if (subject) filters.subject = subject;
  const section = sp.get("section");
  if (section) filters.section = section;
  const difficulty = sp.get("difficulty");
  if (difficulty) filters.difficulty = difficulty;
  const topic = sp.get("topic");
  if (topic) filters.topic = topic;
  if (sp.get("enriched_only") === "true") filters.enriched_only = true;

  const questions = queryQuestions(filters);
  const total = countQuestions(filters);

  if (!reveal) {
    questions.forEach((q) => {
      q.correct_answer = "";
      q.explanation = "";
      q.enrichment = null;
    });
  }

  return NextResponse.json({
    questions,
    total_available: total,
  });
}
