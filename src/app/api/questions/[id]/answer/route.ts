import { NextRequest, NextResponse } from "next/server";
import { getQuestionById, recordAttempt } from "@/lib/db";

/**
 * POST /api/questions/[id]/answer
 *
 * Score an answer for a question server-side. This is the single endpoint
 * the practice UI calls when a user commits an option:
 *   - records the attempt in attempt_stats (times_answered / times_correct)
 *   - returns correctness verdict, the correct answer, and the worked
 *     solution / explanation so the UI can render feedback
 *
 * Body: { "answer": "C", "time_ms"?: number }
 *
 * The answer must be a valid option letter for the question. Invalid letters
 * are rejected with 400 (no scoring row is written).
 */
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  let body: { answer?: unknown; time_ms?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const answer = typeof body.answer === "string" ? body.answer.trim().toUpperCase() : "";
  if (!answer || !/^[A-Z]$/.test(answer)) {
    return NextResponse.json({ error: "Missing or invalid 'answer'" }, { status: 400 });
  }

  const timeMs = typeof body.time_ms === "number" && Number.isFinite(body.time_ms) ? body.time_ms : undefined;

  const question = getQuestionById(id);
  if (!question) {
    return NextResponse.json({ error: "Question not found" }, { status: 404 });
  }

  if (!(answer in question.options)) {
    return NextResponse.json(
      { error: `Option '${answer}' is not valid for this question` },
      { status: 400 }
    );
  }

  const isCorrect = answer === question.correct_answer;
  // Best-effort scoring record — never fail a submission because the stats
  // write failed.
  try {
    recordAttempt(question.id, isCorrect, timeMs);
  } catch (err) {
    console.warn("[answer] recordAttempt failed", err);
  }

  return NextResponse.json({
    question_id: question.id,
    answer,
    correct: isCorrect,
    correct_answer: question.correct_answer,
    explanation: question.explanation ?? "",
    explanation_images: question.explanation_images ?? [],
    enrichment: question.enrichment ?? null,
  });
}
