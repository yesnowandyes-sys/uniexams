import { NextResponse } from "next/server";
import { getExamStats, getEnrichmentFacets, countQuestions } from "@/lib/db";

/**
 * GET /api/questions/stats
 *
 * Returns corpus statistics: question counts per exam type, available years,
 * modules, and subjects, plus enrichment-derived facets (difficulty spread,
 * topic coverage) for filter UIs.
 */
export async function GET() {
  const stats = getExamStats();
  const total = countQuestions();
  const verifiedTotal = countQuestions({ verified_only: true });
  const facets = getEnrichmentFacets();

  return NextResponse.json({
    total_questions: total,
    verified_questions: verifiedTotal,
    by_exam: stats,
    enrichment: facets,
  });
}
