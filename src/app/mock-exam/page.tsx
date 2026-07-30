"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { C, SH, DIFF_META, type DiffKey } from "@/lib/constants";
import type { Question as DbQuestion, Enrichment } from "@/lib/db";
import { recordAttempt } from "@/lib/progress";
import { Svg } from "@/components/icons";
import { Bar, Pill, KBD, Wordmark, Label } from "@/components/atoms";
import { ProgressBar } from "@/components/ProgressBar";
import { QuestionCard } from "@/components/QuestionCard";
import { MathText } from "@/components/MathText";

/**
 * MockExam — timed, full-length practice exam (ESA-18 follow-up).
 *
 * Distinct from /practice:
 *   - 20 mixed questions, no immediate feedback
 *   - Count-up timer (no fixed time limit for now; ESAT spec is untimed per
 *     question but the exam session is 2h. We let the user self-pace and
 *     report total time taken on the results screen.)
 *   - Single "Submit Exam" action grades all answers in one batch
 *   - Results screen reveals per-question correctness, full solutions,
 *     breakdown by subject, and time-per-question estimate
 *
 * Phase state machine:
 *   "intro" → "exam" → "results"
 */

type Phase = "intro" | "exam" | "results";

type StatsResp = {
  total_questions: number;
  by_exam: Record<
    string,
    { count: number; years: string[]; modules: string[] }
  >;
};

type GradedAnswer = {
  correct: boolean;
  correct_answer: string;
  explanation: string;
  explanation_images: string[];
  enrichment: Enrichment | null;
};

const EXAM_SIZE = 20;
const EXAM_LABELS: Record<string, string> = {
  esat: "ESAT",
  engaa: "ENGAA (legacy)",
  nsaa: "NSAA (legacy)",
  nsaa_s2: "NSAA Section 2 (legacy)",
  tmua: "TMUA (legacy)",
};

function prettyExam(k: string): string {
  return EXAM_LABELS[k] ?? k.toUpperCase();
}

function normDifficulty(d: string | undefined): DiffKey {
  if (!d) return "Medium";
  const k = d.toLowerCase();
  if (k.startsWith("easy")) return "Easy";
  if (k.startsWith("very")) return "Very Hard";
  if (k.startsWith("hard")) return "Hard";
  return "Medium";
}

function deriveSubject(q: DbQuestion): string {
  if (q.subject) return pretty(q.subject);
  if (q.module) return pretty(q.module);
  return pretty(q.exam_type);
}

function pretty(s: string): string {
  const parts = s.replace(/_/g, " ").split(/\s+/);
  return parts
    .map((p) => {
      if (/^\d+$/.test(p)) return p;
      const m = p.match(/^([a-zA-Z]+)(\d+)$/);
      if (m) return m[1].charAt(0).toUpperCase() + m[1].slice(1) + " " + m[2];
      return p.charAt(0).toUpperCase() + p.slice(1);
    })
    .join(" ")
    .replace(/\bNsa a\b/i, "NSAA")
    .replace(/\bTmua\b/i, "TMUA")
    .replace(/\bEngaa\b/i, "ENGAA")
    .replace(/\bEsat\b/i, "ESAT");
}

function imageUrl(filename: string): string {
  const enc = filename.split("/").map(encodeURIComponent).join("/");
  return filename.includes("/")
    ? `/api/corpus/${enc}`
    : `/api/corpus/images/${enc}`;
}

function formatMSS(ms: number): string {
  const totalSec = Math.max(0, Math.round(ms / 1000));
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function MockExamPage() {
  const [phase, setPhase] = useState<Phase>("intro");
  const [questions, setQuestions] = useState<DbQuestion[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [ans, setAns] = useState<Record<string, string>>({});
  const ansRef = useRef<Record<string, string>>({});
  const [hovOpt, setHovOpt] = useState<string | null>(null);
  const [graded, setGraded] = useState<Record<string, GradedAnswer> | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [stats, setStats] = useState<StatsResp | null>(null);

  // Exam timer
  const [elapsedMs, setElapsedMs] = useState(0);
  const startedAtRef = useRef<number | null>(null);
  const perQuestionStartRef = useRef<number | null>(null);
  const [perQuestionMs, setPerQuestionMs] = useState<Record<string, number>>({});

  const fetchIdRef = useRef(0);

  useEffect(() => {
    ansRef.current = ans;
  }, [ans]);

  // Load corpus stats for the intro screen.
  useEffect(() => {
    let cancelled = false;
    fetch("/api/questions/stats")
      .then((r) => r.json())
      .then((s: StatsResp) => {
        if (!cancelled) setStats(s);
      })
      .catch(() => {
        /* non-critical */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Timer tick — only during exam phase.
  useEffect(() => {
    if (phase !== "exam") return;
    const t = setInterval(() => {
      if (startedAtRef.current !== null) {
        setElapsedMs(Date.now() - startedAtRef.current);
      }
    }, 1000);
    return () => clearInterval(t);
  }, [phase]);

  // Track per-question time. Reset on index change.
  useEffect(() => {
    if (phase !== "exam") return;
    perQuestionStartRef.current = Date.now();
  }, [idx, phase]);

  const loadExam = useCallback(async () => {
    const myId = ++fetchIdRef.current;
    setQuestions(null);
    setLoadError(null);
    setAns({});
    ansRef.current = {};
    setIdx(0);
    setHovOpt(null);
    setGraded(null);
    setPerQuestionMs({});
    setElapsedMs(0);

    try {
      const url = new URL("/api/questions/random", window.location.origin);
      url.searchParams.set("count", String(EXAM_SIZE));
      url.searchParams.set("reveal", "false");
      const r = await fetch(url.toString());
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data: { questions: DbQuestion[]; total_available: number } =
        await r.json();
      if (myId !== fetchIdRef.current) return;
      if (!data.questions || data.questions.length === 0) {
        setLoadError("No questions available.");
        return;
      }
      setQuestions(data.questions);
      startedAtRef.current = Date.now();
      perQuestionStartRef.current = Date.now();
      setPhase("exam");
    } catch (e) {
      if (myId !== fetchIdRef.current) return;
      setLoadError((e as Error).message || "Failed to load questions.");
    }
  }, []);

  const pick = useCallback(
    (letter: string) => {
      const list = questions;
      if (!list || phase !== "exam") return;
      const qid = list[idx]?.id;
      if (!qid) return;
      // In mock exam mode, allow changing the answer until submit.
      ansRef.current[qid] = letter;
      setAns((prev) => ({ ...prev, [qid]: letter }));
    },
    [idx, questions, phase]
  );

  // Keyboard shortcuts (similar to practice but no solution toggle).
  useEffect(() => {
    if (phase !== "exam") return;
    const h = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target &&
        ["SELECT", "INPUT", "TEXTAREA"].includes(target.tagName)
      )
        return;
      const list = questions;
      if (!list) return;
      const k = e.key;

      if (/^[1-9]$/.test(k)) {
        const letterIdx = parseInt(k, 10) - 1;
        const opts = Object.keys(list[idx]?.options ?? {}).sort();
        if (letterIdx < opts.length) pick(opts[letterIdx]);
        return;
      }
      if (/^[a-i]$/i.test(k)) {
        const L = k.toUpperCase();
        if (list[idx]?.options?.[L]) pick(L);
        return;
      }
      if (k === "ArrowRight" || k === "Enter") {
        if (idx < list.length - 1) setIdx((i) => i + 1);
        return;
      }
      if (k === "ArrowLeft" && idx > 0) setIdx((i) => i - 1);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [idx, questions, pick, phase]);

  // Submit the exam: grade all answers.
  const submitExam = useCallback(async () => {
    const list = questions;
    if (!list || submitting) return;
    setSubmitting(true);

    // Capture per-question time up to submission.
    const finalPerQ: Record<string, number> = { ...perQuestionMs };
    if (perQuestionStartRef.current !== null) {
      const current = list[idx]?.id;
      if (current) {
        const delta = Date.now() - perQuestionStartRef.current;
        finalPerQ[current] = (finalPerQ[current] ?? 0) + delta;
      }
    }
    setPerQuestionMs(finalPerQ);

    const out: Record<string, GradedAnswer> = {};
    await Promise.all(
      list.map(async (q) => {
        const letter = ansRef.current[q.id];
        // Always record the attempt server-side (even if blank → incorrect).
        try {
          if (letter) {
            const r = await fetch(
              `/api/questions/${encodeURIComponent(q.id)}/answer`,
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  answer: letter,
                  time_ms: finalPerQ[q.id],
                }),
              }
            );
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const scored: GradedAnswer = await r.json();
            out[q.id] = scored;

            // Record into client-side progress log.
            recordAttempt({
              questionId: q.id,
              examType: q.exam_type,
              module: q.module ?? "",
              correct: scored.correct,
              timeMs: finalPerQ[q.id],
            });
          } else {
            // Unanswered — record as incorrect without a server call.
            out[q.id] = {
              correct: false,
              correct_answer: q.correct_answer,
              explanation: q.explanation ?? "",
              explanation_images: q.explanation_images ?? [],
              enrichment: q.enrichment ?? null,
            };
          }
        } catch {
          // Fallback: use the local copy's correct_answer if available.
          out[q.id] = {
            correct: false,
            correct_answer: q.correct_answer ?? "",
            explanation: q.explanation ?? "",
            explanation_images: q.explanation_images ?? [],
            enrichment: q.enrichment ?? null,
          };
        }
      })
    );

    setGraded(out);
    setPhase("results");
    setSubmitting(false);
    window.scrollTo({ top: 0 });
  }, [questions, submitting, idx, perQuestionMs]);

  const list = questions;
  const total = list?.length ?? EXAM_SIZE;
  const current = list?.[idx];
  const chosen = current ? ans[current.id] ?? null : null;
  const answeredCount = list
    ? list.filter((q) => ans[q.id]).length
    : 0;

  // ── INTRO ──
  if (phase === "intro") {
    return (
      <Shell>
        <div
          style={{
            maxWidth: 680,
            margin: "0 auto",
            padding: "3rem 1.5rem",
          }}
        >
          <div style={{ marginBottom: "1.75rem", textAlign: "center" }}>
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: 16,
                background: C.blue,
                margin: "0 auto 1.25rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: SH.blue,
              }}
            >
              <Svg icon="pencil" size={28} col="#fff" sw={1.8} />
            </div>
            <h1
              style={{
                fontSize: "2rem",
                fontWeight: 700,
                color: C.text,
                letterSpacing: "-0.025em",
                margin: "0 0 8px",
              }}
            >
              Mock Exam
            </h1>
            <p
              style={{
                fontSize: "0.9375rem",
                color: C.sec,
                lineHeight: 1.7,
                margin: 0,
              }}
            >
              {EXAM_SIZE} mixed-topic questions drawn at real ESAT difficulty.
              You won&apos;t see correctness feedback until you submit — just like
              the real exam.
            </p>
          </div>

          <div
            style={{
              background: C.surf,
              border: `1px solid ${C.bdr}`,
              borderRadius: 14,
              padding: "1.5rem 1.75rem",
              marginBottom: "1.25rem",
              boxShadow: SH.card,
            }}
          >
            <Label col={C.ter} mb={14}>
              What to expect
            </Label>
            <ul
              style={{
                margin: 0,
                padding: 0,
                listStyle: "none",
                display: "flex",
                flexDirection: "column",
                gap: 12,
              }}
            >
              {[
                {
                  icon: "bolt" as const,
                  title: `${EXAM_SIZE} questions`,
                  desc: "Random mixed subjects, weighted by what the ESAT actually covers.",
                },
                {
                  icon: "clock" as const,
                  title: "Self-paced timer",
                  desc: "Count-up timer tracks your total time. Pause by leaving the page is not supported — submit when ready.",
                },
                {
                  icon: "eye" as const,
                  title: "No feedback mid-exam",
                  desc: "Answers lock in your selection but won't reveal correctness. Change answers freely before submitting.",
                },
                {
                  icon: "check" as const,
                  title: "Full results review",
                  desc: "After submit: per-question breakdown, worked solutions, time-per-question, and subject analysis.",
                },
              ].map(({ icon, title, desc }) => (
                <li
                  key={title}
                  style={{
                    display: "flex",
                    gap: 12,
                    alignItems: "flex-start",
                  }}
                >
                  <div
                    style={{
                      width: 30,
                      height: 30,
                      borderRadius: 8,
                      background: C.lite,
                      border: `1px solid ${C.liteb}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <Svg icon={icon} size={14} col={C.mid} sw={2} />
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: "0.875rem",
                        fontWeight: 600,
                        color: C.text,
                        marginBottom: 2,
                      }}
                    >
                      {title}
                    </div>
                    <div
                      style={{
                        fontSize: "0.8125rem",
                        color: C.sec,
                        lineHeight: 1.55,
                      }}
                    >
                      {desc}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {loadError && (
            <div
              style={{
                background: C.rLite,
                border: `1px solid ${C.rBdr}`,
                borderRadius: 10,
                padding: "0.75rem 1rem",
                marginBottom: "1rem",
                color: C.red,
                fontSize: "0.8125rem",
                fontWeight: 500,
              }}
            >
              {loadError}
            </div>
          )}

          <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
            <button
              onClick={loadExam}
              disabled={!list && loadError !== null}
              className="btn-primary"
              style={{
                padding: "12px 28px",
                borderRadius: 10,
                border: "none",
                background: C.mid,
                color: "#fff",
                fontFamily: "Inter, sans-serif",
                fontWeight: 600,
                fontSize: "0.9375rem",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                boxShadow: SH.blue,
              }}
            >
              <Svg icon="play" size={14} col="#fff" sw={2.5} />
              Begin Mock Exam
            </button>
            <a
              href="/practice"
              className="btn-ghost"
              style={{
                padding: "12px 20px",
                borderRadius: 10,
                border: `1px solid ${C.bdr}`,
                background: C.surf,
                color: C.sec,
                fontFamily: "Inter, sans-serif",
                fontWeight: 500,
                fontSize: "0.9375rem",
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <Svg icon="arrowL" size={13} col={C.sec} sw={2} />
              Back to Practice
            </a>
          </div>

          {stats && (
            <div
              style={{
                marginTop: "2rem",
                textAlign: "center",
                fontSize: "0.75rem",
                color: C.ter,
                fontFamily: '"JetBrains Mono", monospace',
              }}
            >
              Drawing from {stats.total_questions.toLocaleString()} questions in
              the corpus
            </div>
          )}
        </div>
      </Shell>
    );
  }

  // ── RESULTS ──
  if (phase === "results" && list && graded) {
    return (
      <ResultsScreen
        questions={list}
        ans={ans}
        graded={graded}
        perQuestionMs={perQuestionMs}
        elapsedMs={elapsedMs}
        onRestart={loadExam}
      />
    );
  }

  // ── EXAM ──
  return (
    <Shell>
      {/* ── Header with timer ── */}
      <header
        style={{
          background: C.surf,
          height: 58,
          borderBottom: `1px solid ${C.bdr}`,
          display: "flex",
          alignItems: "center",
          padding: "0 1.75rem",
          flexShrink: 0,
          position: "sticky",
          top: 0,
          zIndex: 100,
          gap: 16,
        }}
      >
        <a
          href="/"
          className="btn-ghost"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            background: "none",
            border: "none",
            cursor: "pointer",
            color: C.sec,
            fontSize: "0.8125rem",
            fontWeight: 500,
            fontFamily: "Inter, sans-serif",
            padding: "5px 10px",
            borderRadius: 7,
            textDecoration: "none",
          }}
        >
          <Svg icon="arrowL" size={14} col={C.sec} sw={1.8} />
          Exit
        </a>
        <div style={{ width: 1, height: 20, background: C.bdr }} />
        <Wordmark />
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: C.ter,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          Mock Exam
        </span>

        {/* Timer */}
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: C.lite,
              border: `1px solid ${C.liteb}`,
              borderRadius: 8,
              padding: "5px 12px",
            }}
          >
            <Svg icon="clock" size={13} col={C.mid} sw={2} />
            <span
              style={{
                fontFamily: '"JetBrains Mono", monospace',
                fontWeight: 700,
                color: C.mid,
                fontSize: "0.875rem",
                letterSpacing: "-0.01em",
                minWidth: 48,
                textAlign: "right",
              }}
            >
              {formatMSS(elapsedMs)}
            </span>
          </div>

          {/* Answered count */}
          <div
            style={{
              fontSize: "0.8125rem",
              color: C.sec,
            }}
          >
            <span
              style={{
                fontFamily: '"JetBrains Mono", monospace',
                fontWeight: 700,
                color: C.text,
              }}
            >
              {answeredCount}
            </span>
            <span style={{ color: C.ter }}> / {total}</span>
          </div>

          <button
            onClick={submitExam}
            disabled={submitting}
            className="btn-primary"
            style={{
              padding: "7px 16px",
              borderRadius: 8,
              border: "none",
              background: C.green,
              color: "#fff",
              fontFamily: "Inter, sans-serif",
              fontWeight: 600,
              fontSize: "0.8125rem",
              cursor: submitting ? "default" : "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              opacity: submitting ? 0.7 : 1,
            }}
          >
            <Svg icon="check" size={13} col="#fff" sw={2.5} />
            {submitting ? "Grading…" : "Submit Exam"}
          </button>
        </div>

        {/* Thin progress stripe */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: 2,
            background: C.bdr,
          }}
        >
          <div
            style={{
              height: "100%",
              borderRadius: 1,
              width: `${
                total ? (answeredCount / total) * 100 : 0
              }%`,
              background: C.mid,
              transition:
                "width 0.45s cubic-bezier(0.16,1,0.3,1), background 0.3s",
            }}
          />
        </div>
      </header>

      {/* ── Main layout ── */}
      <div
        className="practice-layout"
        style={{
          flex: 1,
          maxWidth: 1200,
          width: "100%",
          margin: "0 auto",
          padding: "1.5rem 1.75rem",
          display: "flex",
          gap: "1.5rem",
          boxSizing: "border-box",
        }}
      >
        {/* ══ LEFT: Question pane ══ */}
        <div style={{ flex: "1 1 0", minWidth: 0 }}>
          {/* Question navigator grid */}
          {(list?.length ?? 0) > 0 && (
            <div
              style={{
                display: "flex",
                gap: 6,
                marginBottom: "1.25rem",
                flexWrap: "wrap",
              }}
            >
              {list!.map((q, i) => {
                const a = ans[q.id];
                const cur = i === idx;
                return (
                  <button
                    key={q.id}
                    onClick={() => setIdx(i)}
                    className="q-num-btn"
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 8,
                      border: `2px solid ${cur ? C.mid : a ? C.liteb : C.bdr}`,
                      background: a ? C.lite : C.surf,
                      color: a ? C.mid : cur ? C.mid : C.ter,
                      fontFamily: '"JetBrains Mono", monospace',
                      fontWeight: cur ? 700 : 500,
                      fontSize: "0.75rem",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxSizing: "border-box",
                      boxShadow: cur ? `0 0 0 3px ${C.lite}` : "none",
                    }}
                  >
                    {i + 1}
                  </button>
                );
              })}
            </div>
          )}

          {/* Loading / error / question */}
          {!list && !loadError && <LoadingState />}
          {loadError && (
            <ErrorState
              msg={loadError}
              onRetry={() => {
                setPhase("intro");
                setLoadError(null);
              }}
            />
          )}

          {current && (
            <MockQuestionView
              question={current}
              index={idx}
              total={total}
              chosen={chosen}
              onChoose={pick}
              hovOpt={hovOpt}
              onHoverOption={setHovOpt}
            />
          )}

          {/* Prev / Next */}
          {list && list.length > 0 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginTop: 4,
              }}
            >
              <button
                onClick={() => idx > 0 && setIdx((i) => i - 1)}
                className="nav-btn"
                disabled={idx === 0}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "7px 14px",
                  borderRadius: 8,
                  border: `1px solid ${C.bdr}`,
                  background: C.surf,
                  color: idx === 0 ? C.ter : C.sec,
                  fontSize: "0.8125rem",
                  fontWeight: 500,
                  fontFamily: "Inter, sans-serif",
                  opacity: idx === 0 ? 0.4 : 1,
                  cursor: idx === 0 ? "default" : "pointer",
                }}
              >
                <Svg icon="chevL" size={13} col="currentColor" sw={2} />
                Previous
              </button>
              <button
                onClick={() => idx < total - 1 && setIdx((i) => i + 1)}
                className="nav-btn"
                disabled={idx === total - 1}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "7px 14px",
                  borderRadius: 8,
                  border: `1px solid ${C.bdr}`,
                  background: C.surf,
                  color: idx === total - 1 ? C.ter : C.sec,
                  fontSize: "0.8125rem",
                  fontWeight: 500,
                  fontFamily: "Inter, sans-serif",
                  opacity: idx === total - 1 ? 0.4 : 1,
                  cursor: idx === total - 1 ? "default" : "pointer",
                }}
              >
                Next
                <Svg icon="chevR" size={13} col="currentColor" sw={2} />
              </button>

              {/* Submit button at the end of the exam */}
              {idx === total - 1 && (
                <button
                  onClick={submitExam}
                  disabled={submitting}
                  className="btn-primary"
                  style={{
                    marginLeft: "auto",
                    padding: "7px 18px",
                    borderRadius: 8,
                    border: "none",
                    background: C.green,
                    color: "#fff",
                    fontFamily: "Inter, sans-serif",
                    fontWeight: 600,
                    fontSize: "0.8125rem",
                    cursor: submitting ? "default" : "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    opacity: submitting ? 0.7 : 1,
                  }}
                >
                  <Svg icon="check" size={13} col="#fff" sw={2.5} />
                  {submitting ? "Grading…" : "Submit Exam"}
                </button>
              )}
            </div>
          )}
        </div>

        {/* ══ RIGHT: Sidebar ══ */}
        <div className="practice-sidebar" style={{ width: 268, flexShrink: 0 }}>
          {/* Answered progress */}
          <div
            style={{
              background: C.surf,
              border: `1px solid ${C.bdr}`,
              borderRadius: 12,
              padding: "1.1rem 1.2rem",
              marginBottom: 12,
              boxShadow: SH.card,
            }}
          >
            <Label col={C.ter} mb={10}>
              Exam Progress
            </Label>
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 5,
                marginBottom: 10,
              }}
            >
              <span
                style={{
                  fontFamily: '"JetBrains Mono", monospace',
                  fontSize: "1.875rem",
                  fontWeight: 700,
                  color: C.mid,
                  lineHeight: 1,
                }}
              >
                {answeredCount}
              </span>
              <span style={{ fontSize: "0.875rem", color: C.ter }}>
                of {total} answered
              </span>
            </div>
            <ProgressBar
              pct={total ? (answeredCount / total) * 100 : 0}
              color={C.mid}
              h={4}
            />
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: 10,
                fontSize: "0.75rem",
                color: C.ter,
              }}
            >
              <span>
                Remaining:{" "}
                <span
                  style={{
                    fontFamily: '"JetBrains Mono",monospace',
                    fontWeight: 700,
                    color: C.sec,
                  }}
                >
                  {total - answeredCount}
                </span>
              </span>
              <span>
                Time:{" "}
                <span
                  style={{
                    fontFamily: '"JetBrains Mono",monospace',
                    fontWeight: 700,
                    color: C.mid,
                  }}
                >
                  {formatMSS(elapsedMs)}
                </span>
              </span>
            </div>
          </div>

          {/* Unanswered list */}
          <div
            style={{
              background: C.surf,
              border: `1px solid ${C.bdr}`,
              borderRadius: 12,
              padding: "1.1rem 1.2rem",
              marginBottom: 12,
              boxShadow: SH.card,
            }}
          >
            <Label col={C.ter} mb={10}>
              Jump to question
            </Label>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(5, 1fr)",
                gap: 6,
              }}
            >
              {(list ?? []).map((q, i) => {
                const a = ans[q.id];
                const cur = i === idx;
                return (
                  <button
                    key={q.id}
                    onClick={() => setIdx(i)}
                    style={{
                      aspectRatio: "1",
                      borderRadius: 7,
                      border: `1.5px solid ${
                        cur ? C.mid : a ? C.liteb : C.bdr
                      }`,
                      background: a ? C.lite : C.surf,
                      color: a ? C.mid : C.ter,
                      fontFamily: '"JetBrains Mono", monospace',
                      fontWeight: a ? 700 : 500,
                      fontSize: "0.75rem",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      padding: 0,
                    }}
                  >
                    {i + 1}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Exam info */}
          <div
            style={{
              background: C.lite,
              border: `1px solid ${C.liteb}`,
              borderRadius: 12,
              padding: "10px 14px",
              display: "flex",
              alignItems: "flex-start",
              gap: 8,
            }}
          >
            <Svg icon="info" size={14} col={C.mid} sw={2} />
            <div
              style={{
                fontSize: "0.75rem",
                color: C.sec,
                lineHeight: 1.6,
              }}
            >
              You can change answers freely until you submit. Correctness is
              hidden until the exam is graded.
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
}

// ── MockQuestionView (no immediate feedback) ──

function MockQuestionView({
  question,
  index,
  total,
  chosen,
  onChoose,
  hovOpt,
  onHoverOption,
}: {
  question: DbQuestion;
  index: number;
  total: number;
  chosen: string | null;
  onChoose: (letter: string) => void;
  hovOpt: string | null;
  onHoverOption: (letter: string | null) => void;
}) {
  const diff = normDifficulty(question.enrichment?.difficulty);
  const dm = DIFF_META[diff];
  const subject = deriveSubject(question);
  const topic = question.enrichment?.topics?.[0];
  const optionLetters = Object.keys(question.options).sort();

  return (
    <div>
      {/* Meta row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: "1rem",
          flexWrap: "wrap",
        }}
      >
        <Pill bg={C.lite} col={C.mid} bdr={C.liteb}>
          {subject}
        </Pill>
        <Pill bg={dm.bg} col={dm.col} bdr={dm.bdr}>
          {diff}
        </Pill>
        {topic && (
          <Pill bg={C.alt} col={C.sec} bdr={C.bdr}>
            {topic}
          </Pill>
        )}
        {question.year && (
          <Pill bg={C.alt} col={C.ter} bdr={C.bdr}>
            {question.year}
          </Pill>
        )}
        <div
          style={{
            marginLeft: "auto",
            fontSize: "0.75rem",
            color: C.ter,
            fontFamily: '"JetBrains Mono", monospace',
          }}
        >
          {question.id}
        </div>
      </div>

      {/* Question card */}
      <QuestionCard style={{ marginBottom: "0.875rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "0.875rem",
          }}
        >
          <Label col={C.ter}>
            Question {index + 1} of {total}
          </Label>
          <Pill bg={dm.bg} col={dm.col} bdr={dm.bdr}>
            {diff}
          </Pill>
        </div>
        <MathText
          as="p"
          style={{
            margin: 0,
            fontSize: "0.9375rem",
            lineHeight: 1.85,
            color: C.text,
            fontWeight: 400,
          }}
        >
          {question.question_text}
        </MathText>

        {question.question_images.length > 0 && (
          <div
            style={{
              marginTop: "1rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
              alignItems: "flex-start",
            }}
          >
            {question.question_images.map((img) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={img}
                src={imageUrl(img)}
                alt={img}
                style={{
                  maxWidth: "100%",
                  borderRadius: 8,
                  border: `1px solid ${C.bdr}`,
                  background: C.surf,
                }}
                loading="lazy"
              />
            ))}
          </div>
        )}
      </QuestionCard>

      {/* Options — no feedback styling, just selection state */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          marginBottom: "0.875rem",
        }}
      >
        {optionLetters.map((l, i) => {
          const selected = chosen === l;
          const isHov = hovOpt === l && chosen !== l;
          const text = question.options[l] ?? "";
          return (
            <button
              key={l}
              onClick={() => onChoose(l)}
              onMouseEnter={() => onHoverOption(l)}
              onMouseLeave={() => onHoverOption(null)}
              className="opt-btn"
              style={{
                display: "flex",
                alignItems: "center",
                padding: "0.75rem 1rem",
                border: `2px solid ${
                  selected ? C.mid : isHov ? C.liteb : C.bdr
                }`,
                borderRadius: 10,
                background: selected ? C.lite : isHov ? C.alt : C.surf,
                fontFamily: "Inter,sans-serif",
                textAlign: "left",
                width: "100%",
                boxSizing: "border-box",
                cursor: "pointer",
              }}
            >
              <span
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 7,
                  flexShrink: 0,
                  background: selected ? C.mid : isHov ? C.mid : C.alt,
                  color: selected || isHov ? "#fff" : C.sec,
                  fontFamily: '"JetBrains Mono",monospace',
                  fontWeight: 700,
                  fontSize: "0.8125rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "background 0.12s, color 0.12s",
                  marginRight: "0.875rem",
                }}
              >
                {l}
              </span>
              <span
                style={{
                  flex: 1,
                  color: selected ? C.text : C.text,
                  fontSize: "0.875rem",
                  lineHeight: 1.6,
                  fontWeight: selected ? 500 : 400,
                }}
              >
                <MathText>{text}</MathText>
                {i < 9 && (
                  <span
                    style={{
                      marginLeft: 8,
                      opacity: 0.45,
                      fontSize: "0.6875rem",
                      fontFamily: '"JetBrains Mono",monospace',
                    }}
                  >
                    [{i + 1}]
                  </span>
                )}
              </span>
              {selected && (
                <div
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    background: C.mid,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    marginLeft: 10,
                  }}
                >
                  <Svg icon="check" size={11} col="#fff" sw={2.5} />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Results screen ──

function ResultsScreen({
  questions,
  ans,
  graded,
  perQuestionMs,
  elapsedMs,
  onRestart,
}: {
  questions: DbQuestion[];
  ans: Record<string, string>;
  graded: Record<string, GradedAnswer>;
  perQuestionMs: Record<string, number>;
  elapsedMs: number;
  onRestart: () => void;
}) {
  const [revealedQids, setRevealedQids] = useState<Set<string>>(new Set());

  const total = questions.length;
  const correctCount = questions.filter(
    (q) => graded[q.id]?.correct
  ).length;
  const unanswered = questions.filter((q) => !ans[q.id]).length;
  const pct = total > 0 ? Math.round((correctCount / total) * 100) : 0;

  // Per-subject breakdown.
  const bySubject = new Map<
    string,
    { answered: number; correct: number }
  >();
  for (const q of questions) {
    const key = deriveSubject(q);
    const e = bySubject.get(key) ?? { answered: 0, correct: 0 };
    e.answered++;
    if (graded[q.id]?.correct) e.correct++;
    bySubject.set(key, e);
  }
  const subjectRows = Array.from(bySubject.entries())
    .map(([k, v]) => ({
      subject: k,
      answered: v.answered,
      correct: v.correct,
      pct: v.answered > 0 ? Math.round((v.correct / v.answered) * 100) : 0,
    }))
    .sort((a, b) => b.pct - a.pct);

  const avgPerQ =
    total > 0
      ? Math.round(
          questions.reduce((s, q) => s + (perQuestionMs[q.id] ?? 0), 0) / total
        )
      : 0;

  const toggleReveal = (qid: string) => {
    setRevealedQids((prev) => {
      const next = new Set(prev);
      if (next.has(qid)) next.delete(qid);
      else next.add(qid);
      return next;
    });
  };

  const headline =
    pct >= 80 ? "Outstanding work" : pct >= 60 ? "Strong performance" : pct >= 40 ? "Keep going" : "Needs attention";

  return (
    <Shell>
      <header
        style={{
          background: C.surf,
          height: 58,
          borderBottom: `1px solid ${C.bdr}`,
          display: "flex",
          alignItems: "center",
          padding: "0 1.75rem",
          flexShrink: 0,
          position: "sticky",
          top: 0,
          zIndex: 100,
          gap: 16,
        }}
      >
        <a
          href="/"
          className="btn-ghost"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            background: "none",
            border: "none",
            cursor: "pointer",
            color: C.sec,
            fontSize: "0.8125rem",
            fontWeight: 500,
            fontFamily: "Inter, sans-serif",
            padding: "5px 10px",
            borderRadius: 7,
            textDecoration: "none",
          }}
        >
          <Svg icon="arrowL" size={14} col={C.sec} sw={1.8} />
          Dashboard
        </a>
        <div style={{ width: 1, height: 20, background: C.bdr }} />
        <Wordmark />
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: C.ter,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          Mock Exam Results
        </span>
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            gap: 8,
          }}
        >
          <a
            href="/practice"
            className="btn-ghost"
            style={{
              padding: "6px 14px",
              borderRadius: 8,
              border: `1px solid ${C.bdr}`,
              background: C.surf,
              color: C.sec,
              fontFamily: "Inter, sans-serif",
              fontWeight: 500,
              fontSize: "0.8125rem",
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Svg icon="bolt" size={12} col={C.sec} sw={2} />
            Practice
          </a>
          <button
            onClick={onRestart}
            className="btn-primary"
            style={{
              padding: "6px 16px",
              borderRadius: 8,
              border: "none",
              background: C.mid,
              color: "#fff",
              fontFamily: "Inter, sans-serif",
              fontWeight: 600,
              fontSize: "0.8125rem",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Svg icon="play" size={12} col="#fff" sw={2.5} />
            New Exam
          </button>
        </div>
      </header>

      <div
        style={{
          maxWidth: 920,
          margin: "0 auto",
          padding: "1.75rem 1.75rem 3rem",
        }}
      >
        {/* ── Headline ── */}
        <div
          style={{
            background: C.surf,
            border: `1px solid ${C.bdr}`,
            borderRadius: 14,
            padding: "1.75rem 2rem",
            marginBottom: "1.25rem",
            boxShadow: SH.card,
            display: "flex",
            alignItems: "center",
            gap: 24,
          }}
        >
          <div
            style={{
              width: 88,
              height: 88,
              borderRadius: "50%",
              border: `4px solid ${
                pct >= 70 ? C.green : pct >= 50 ? C.amber : C.red
              }`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <span
              style={{
                fontFamily: '"JetBrains Mono", monospace',
                fontSize: "1.75rem",
                fontWeight: 700,
                color:
                  pct >= 70 ? C.green : pct >= 50 ? C.amber : C.red,
                lineHeight: 1,
              }}
            >
              {pct}%
            </span>
            <span
              style={{
                fontSize: "0.625rem",
                fontWeight: 600,
                color: C.ter,
                marginTop: 4,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Score
            </span>
          </div>
          <div style={{ flex: 1 }}>
            <h1
              style={{
                margin: "0 0 6px",
                fontSize: "1.5rem",
                fontWeight: 700,
                color: C.text,
                letterSpacing: "-0.02em",
              }}
            >
              {headline}
            </h1>
            <div
              style={{
                display: "flex",
                gap: 20,
                fontSize: "0.8125rem",
                color: C.sec,
              }}
            >
              <span>
                <span
                  style={{
                    fontFamily: '"JetBrains Mono", monospace',
                    fontWeight: 700,
                    color: C.green,
                  }}
                >
                  {correctCount}
                </span>{" "}
                correct
              </span>
              <span>
                <span
                  style={{
                    fontFamily: '"JetBrains Mono", monospace',
                    fontWeight: 700,
                    color: C.red,
                  }}
                >
                  {total - correctCount - unanswered}
                </span>{" "}
                incorrect
              </span>
              {unanswered > 0 && (
                <span>
                  <span
                    style={{
                      fontFamily: '"JetBrains Mono", monospace',
                      fontWeight: 700,
                      color: C.ter,
                    }}
                  >
                    {unanswered}
                  </span>{" "}
                  blank
                </span>
              )}
              <span>
                <Svg
                  icon="clock"
                  size={11}
                  col={C.ter}
                  sw={2}
                />
                <span
                  style={{
                    fontFamily: '"JetBrains Mono", monospace',
                    fontWeight: 700,
                    color: C.mid,
                    marginLeft: 4,
                  }}
                >
                  {formatMSS(elapsedMs)}
                </span>{" "}
                total
              </span>
              <span>
                <span
                  style={{
                    fontFamily: '"JetBrains Mono", monospace',
                    fontWeight: 700,
                    color: C.sec,
                  }}
                >
                  {formatMSS(avgPerQ)}
                </span>{" "}
                avg/Q
              </span>
            </div>
          </div>
        </div>

        {/* ── Per-question result grid ── */}
        <div
          style={{
            background: C.surf,
            border: `1px solid ${C.bdr}`,
            borderRadius: 14,
            padding: "1.25rem 1.5rem",
            marginBottom: "1.25rem",
            boxShadow: SH.card,
          }}
        >
          <Label col={C.ter} mb={12}>
            Per-question breakdown — click to reveal solution
          </Label>
          <div
            style={{
              display: "flex",
              gap: 5,
              marginBottom: 14,
              flexWrap: "wrap",
            }}
          >
            {questions.map((q, i) => {
              const g = graded[q.id];
              const ok = g?.correct;
              const blank = !ans[q.id];
              const bg = blank ? C.alt : ok ? C.gLite : C.rLite;
              const bdr = blank ? C.bdr2 : ok ? C.green : C.red;
              const col = blank ? C.ter : ok ? C.green : C.red;
              return (
                <div
                  key={q.id}
                  onClick={() => {
                    document
                      .getElementById(`q-${q.id}`)
                      ?.scrollIntoView({ behavior: "smooth", block: "center" });
                    toggleReveal(q.id);
                  }}
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 7,
                    background: bg,
                    border: `1.5px solid ${bdr}`,
                    color: col,
                    fontFamily: '"JetBrains Mono", monospace',
                    fontWeight: 700,
                    fontSize: "0.75rem",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "transform 0.12s",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLDivElement).style.transform =
                      "scale(1.08)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLDivElement).style.transform =
                      "scale(1)";
                  }}
                  title={`Q${i + 1}: ${blank ? "No answer" : ok ? "Correct" : "Incorrect"}`}
                >
                  {i + 1}
                </div>
              );
            })}
          </div>

          {/* Per-subject table */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 8,
              marginTop: 4,
            }}
          >
            {subjectRows.map((r) => {
              const col =
                r.pct >= 70 ? C.green : r.pct >= 50 ? C.amber : C.red;
              return (
                <div key={r.subject}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "0.8125rem",
                      color: C.sec,
                      marginBottom: 3,
                    }}
                  >
                    <span>{r.subject}</span>
                    <span
                      style={{
                        fontFamily: '"JetBrains Mono", monospace',
                        color: col,
                      }}
                    >
                      {r.correct}/{r.answered} ({r.pct}%)
                    </span>
                  </div>
                  <Bar pct={r.pct} color={col} />
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Full per-question review ── */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          {questions.map((q, i) => {
            const g = graded[q.id];
            const userAns = ans[q.id];
            const ok = g?.correct;
            const blank = !userAns;
            const revealed = revealedQids.has(q.id);
            const col = blank ? C.ter : ok ? C.green : C.red;
            const bg = blank ? C.alt : ok ? C.gLite : C.rLite;
            const bdr = blank ? C.bdr2 : ok ? C.gBdr : C.rBdr;

            return (
              <div
                key={q.id}
                id={`q-${q.id}`}
                style={{
                  background: C.surf,
                  border: `1px solid ${C.bdr}`,
                  borderRadius: 12,
                  boxShadow: SH.card,
                  overflow: "hidden",
                  scrollMarginTop: 80,
                }}
              >
                {/* Result header */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "0.875rem 1.25rem",
                    borderBottom: revealed ? `1px solid ${C.bdr}` : "none",
                    background: bg,
                  }}
                >
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: 7,
                      background: col,
                      color: "#fff",
                      fontFamily: '"JetBrains Mono", monospace',
                      fontWeight: 700,
                      fontSize: "0.75rem",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    {i + 1}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: "0.8125rem",
                        fontWeight: 600,
                        color: C.text,
                      }}
                    >
                      {deriveSubject(q)}
                      {q.year ? ` · ${q.year}` : ""}
                    </div>
                    <div
                      style={{
                        fontSize: "0.6875rem",
                        color: C.ter,
                        fontFamily: '"JetBrains Mono", monospace',
                        marginTop: 2,
                      }}
                    >
                      Your answer:{" "}
                      <span
                        style={{
                          color: blank ? C.ter : col,
                          fontWeight: 700,
                        }}
                      >
                        {userAns ?? "—"}
                      </span>
                      {"  ·  "}
                      Correct:{" "}
                      <span style={{ color: C.green, fontWeight: 700 }}>
                        {g?.correct_answer ?? "?"}
                      </span>
                      {perQuestionMs[q.id] ? (
                        <>
                          {"  ·  "}
                          {formatMSS(perQuestionMs[q.id])}
                        </>
                      ) : null}
                    </div>
                  </div>
                  <button
                    onClick={() => toggleReveal(q.id)}
                    style={{
                      padding: "5px 12px",
                      borderRadius: 7,
                      border: `1px solid ${bdr}`,
                      background: C.surf,
                      color: col,
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      fontFamily: "Inter, sans-serif",
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 5,
                    }}
                  >
                    <Svg
                      icon={revealed ? "eye" : "book"}
                      size={12}
                      col={col}
                      sw={2}
                    />
                    {revealed ? "Hide solution" : "Show solution"}
                  </button>
                </div>

                {/* Question body */}
                <div
                  style={{
                    padding: "1.1rem 1.4rem",
                    display: revealed ? "block" : "none",
                  }}
                >
                  <MathText
                    as="p"
                    style={{
                      margin: "0 0 0.875rem 0",
                      fontSize: "0.9375rem",
                      lineHeight: 1.85,
                      color: C.text,
                    }}
                  >
                    {q.question_text}
                  </MathText>

                  {q.question_images.length > 0 && (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.5rem",
                        marginBottom: "0.875rem",
                      }}
                    >
                      {q.question_images.map((img) => (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          key={img}
                          src={imageUrl(img)}
                          alt={img}
                          style={{
                            maxWidth: "100%",
                            borderRadius: 8,
                            border: `1px solid ${C.bdr}`,
                          }}
                          loading="lazy"
                        />
                      ))}
                    </div>
                  )}

                  {/* Options with correct/incorrect highlight */}
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                      marginBottom: "0.875rem",
                    }}
                  >
                    {Object.keys(q.options).sort().map((l) => {
                      const isCorrect = l === g?.correct_answer;
                      const isUserPick = l === userAns;
                      const showCorrect = isCorrect;
                      const showWrong = isUserPick && !isCorrect;
                      const bgC = showCorrect
                        ? C.gLite
                        : showWrong
                        ? C.rLite
                        : C.surf;
                      const bdrC = showCorrect
                        ? C.green
                        : showWrong
                        ? C.red
                        : C.bdr;
                      const lblBg = showCorrect
                        ? C.green
                        : showWrong
                        ? C.red
                        : C.alt;
                      const lblCol =
                        showCorrect || showWrong ? "#fff" : C.sec;
                      return (
                        <div
                          key={l}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            padding: "0.6rem 0.875rem",
                            border: `2px solid ${bdrC}`,
                            borderRadius: 9,
                            background: bgC,
                          }}
                        >
                          <span
                            style={{
                              width: 26,
                              height: 26,
                              borderRadius: 6,
                              flexShrink: 0,
                              background: lblBg,
                              color: lblCol,
                              fontFamily:
                                '"JetBrains Mono",monospace',
                              fontWeight: 700,
                              fontSize: "0.75rem",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              marginRight: "0.75rem",
                            }}
                          >
                            {l}
                          </span>
                          <span
                            style={{
                              flex: 1,
                              color: C.text,
                              fontSize: "0.8125rem",
                              lineHeight: 1.6,
                            }}
                          >
                            <MathText>{q.options[l]}</MathText>
                          </span>
                          {showCorrect && (
                            <Svg
                              icon="check"
                              size={14}
                              col={C.green}
                              sw={2.5}
                            />
                          )}
                          {showWrong && (
                            <Svg
                              icon="x"
                              size={14}
                              col={C.red}
                              sw={2.5}
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Solution text */}
                  {g?.enrichment?.markdown || g?.explanation ? (
                    <div
                      style={{
                        background: C.lite,
                        border: `1px solid ${C.liteb}`,
                        borderRadius: 9,
                        padding: "1rem 1.25rem",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          marginBottom: "0.5rem",
                        }}
                      >
                        <Svg
                          icon="sparkle"
                          size={13}
                          col={C.mid}
                          sw={1.8}
                        />
                        <span
                          style={{
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            color: C.blue,
                          }}
                        >
                          Worked Solution
                        </span>
                      </div>
                      <MathText
                        as="p"
                        style={{
                          margin: 0,
                          color: C.text,
                          fontSize: "0.8125rem",
                          lineHeight: 1.9,
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {g.enrichment?.markdown || g.explanation}
                      </MathText>
                    </div>
                  ) : (
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: C.ter,
                        fontStyle: "italic",
                      }}
                    >
                      No worked solution available for this question.
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom CTAs */}
        <div
          style={{
            display: "flex",
            gap: 10,
            justifyContent: "center",
            marginTop: "1.75rem",
          }}
        >
          <button
            onClick={onRestart}
            className="btn-primary"
            style={{
              padding: "11px 24px",
              borderRadius: 10,
              border: "none",
              background: C.mid,
              color: "#fff",
              fontFamily: "Inter, sans-serif",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              boxShadow: SH.blue,
            }}
          >
            <Svg icon="play" size={13} col="#fff" sw={2.5} />
            Take Another Exam
          </button>
          <a
            href="/"
            className="btn-ghost"
            style={{
              padding: "11px 20px",
              borderRadius: 10,
              border: `1px solid ${C.bdr}`,
              background: C.surf,
              color: C.sec,
              fontFamily: "Inter, sans-serif",
              fontWeight: 500,
              fontSize: "0.875rem",
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            Back to Dashboard
          </a>
        </div>
      </div>
    </Shell>
  );
}

// ── Shared shell ──

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: "Inter, sans-serif",
        background: C.bg,
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {children}
    </div>
  );
}

function LoadingState() {
  return (
    <div
      style={{
        background: C.surf,
        border: `1px solid ${C.bdr}`,
        borderRadius: 14,
        padding: "3rem 2rem",
        textAlign: "center",
        boxShadow: SH.card,
      }}
    >
      <div
        className="pulse-dot"
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: C.mid,
          margin: "0 auto 1rem",
        }}
      />
      <div style={{ color: C.sec, fontSize: "0.875rem" }}>
        Loading questions…
      </div>
    </div>
  );
}

function ErrorState({ msg, onRetry }: { msg: string; onRetry: () => void }) {
  return (
    <div
      style={{
        background: C.rLite,
        border: `1px solid ${C.rBdr}`,
        borderRadius: 14,
        padding: "2rem",
        textAlign: "center",
      }}
    >
      <div
        style={{
          color: C.red,
          fontSize: "0.9375rem",
          fontWeight: 600,
          marginBottom: 8,
        }}
      >
        {msg}
      </div>
      <button
        onClick={onRetry}
        style={{
          padding: "7px 16px",
          borderRadius: 8,
          border: `1px solid ${C.rBdr}`,
          background: C.surf,
          color: C.red,
          fontSize: "0.8125rem",
          fontWeight: 600,
          fontFamily: "Inter, sans-serif",
          cursor: "pointer",
        }}
      >
        Back
      </button>
    </div>
  );
}
