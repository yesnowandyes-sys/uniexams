import { NextRequest, NextResponse } from "next/server";
import { getQuestionById } from "@/lib/db";

/**
 * GET /api/questions/[id]
 *
 * Returns a single question by ID.
 * By default strips the correct_answer and explanation (practice mode).
 * Use ?reveal=true to include answer + explanation.
 */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const reveal = req.nextUrl.searchParams.get("reveal") === "true";

  const question = getQuestionById(id);
  if (!question) {
    return NextResponse.json({ error: "Question not found" }, { status: 404 });
  }

  if (!reveal) {
    // Strip answer info for practice mode
    return NextResponse.json({
      ...question,
      correct_answer: "",
      explanation: "",
      enrichment: null,
    });
  }

  return NextResponse.json(question);
}
