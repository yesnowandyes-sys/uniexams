import { NextRequest, NextResponse } from "next/server";
import { queryQuestions, countQuestions, type QuestionFilters } from "@/lib/db";

/**
 * GET /api/questions
 *
 * Query params:
 *   exam_type - filter by exam (esat|engaa|nsaa|nsaa_s2|tmua)
 *   year      - filter by year (e.g. "2020", "specimen")
 *   module    - filter by module (e.g. "biology", "chemistry")
 *   subject   - filter by subject
 *   section   - filter by section (s1, s2, p1, p2)
 *   difficulty - filter by enrichment difficulty (Easy|Medium|Hard|Very Hard)
 *   topic     - substring match against topic_code/topic_name/content_code
 *   enriched_only - if "true", only return questions with successful enrichment
 *   limit     - page size (default 50, max 200)
 *   offset    - pagination offset (default 0)
 *   random    - if "true", randomize order
 *   count     - if "true", return only the count
 */
export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;

  if (sp.get("count") === "true") {
    const total = countQuestions(parseFilters(sp));
    return NextResponse.json({ count: total });
  }

  const filters = parseFilters(sp);
  const limit = Math.min(filters.limit ?? 50, 200);
  const offset = filters.offset ?? 0;

  const questions = queryQuestions({ ...filters, limit, offset });
  const total = countQuestions(filters);

  return NextResponse.json({
    questions,
    pagination: {
      limit,
      offset,
      total,
      has_more: offset + questions.length < total,
    },
  });
}

function parseFilters(sp: URLSearchParams): QuestionFilters {
  const filters: QuestionFilters = {};
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
  if (sp.get("verified_only") === "true") filters.verified_only = true;
  if (sp.get("random") === "true") filters.random = true;
  return filters;
}
