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
import styles from "./page.module.css";

/**
 * MockExam — timed, full-length practice exam (ESA-18 follow-up).
 *
 * Distinct from /practice:
 *   - 20 mixed questions, no immediate feedback
 *   - Count-up timer
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
  const [sidebarOpen, setSidebarOpen] = useState(false);

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

            recordAttempt({
              questionId: q.id,
              examType: q.exam_type,
              module: q.module ?? "",
              correct: scored.correct,
              timeMs: finalPerQ[q.id],
            });
          } else {
            out[q.id] = {
              correct: false,
              correct_answer: q.correct_answer,
              explanation: q.explanation ?? "",
              explanation_images: q.explanation_images ?? [],
              enrichment: q.enrichment ?? null,
            };
          }
        } catch {
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
        <div className={styles.intro}>
          <div className={styles.introHeader}>
            <div className={styles.introIcon} style={{ boxShadow: SH.blue }}>
              <Svg icon="pencil" size={28} col="#fff" sw={1.8} />
            </div>
            <h1 className={styles.introTitle}>
              Mock Exam
            </h1>
            <p className={styles.introDesc}>
              {EXAM_SIZE} mixed-topic questions drawn at real ESAT difficulty.
              You won&apos;t see correctness feedback until you submit — just like
              the real exam.
            </p>
          </div>

          <div className={styles.introCard} style={{ boxShadow: SH.card }}>
            <Label col={C.ter} mb={14}>
              What to expect
            </Label>
            <ul className={styles.introList}>
              {[
                { icon: "bolt" as const, title: `${EXAM_SIZE} questions`, desc: "Random mixed subjects, weighted by what the ESAT actually covers." },
                { icon: "clock" as const, title: "Self-paced timer", desc: "Count-up timer tracks your total time. Pause by leaving the page is not supported — submit when ready." },
                { icon: "eye" as const, title: "No feedback mid-exam", desc: "Answers lock in your selection but won't reveal correctness. Change answers freely before submitting." },
                { icon: "check" as const, title: "Full results review", desc: "After submit: per-question breakdown, worked solutions, time-per-question, and subject analysis." },
              ].map(({ icon, title, desc }) => (
                <li key={title} className={styles.introListItem}>
                  <div className={styles.introItemIcon}>
                    <Svg icon={icon} size={14} col={C.mid} sw={2} />
                  </div>
                  <div>
                    <div className={styles.introItemTitle}>{title}</div>
                    <div className={styles.introItemDesc}>{desc}</div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {loadError && (
            <div className={styles.introError}>
              {loadError}
            </div>
          )}

          <div className={styles.introActions}>
            <button
              onClick={loadExam}
              disabled={!list && loadError !== null}
              className={`${styles.introBeginBtn} btn-primary`}
              style={{ boxShadow: SH.blue }}
            >
              <Svg icon="play" size={14} col="#fff" sw={2.5} />
              Begin Mock Exam
            </button>
            <a href="/practice" className={`${styles.introBackBtn} btn-ghost`}>
              <Svg icon="arrowL" size={13} col={C.sec} sw={2} />
              Back to Practice
            </a>
          </div>

          {stats && (
            <div className={styles.introCorpusNote}>
              Drawing from {stats.total_questions.toLocaleString()} questions in the corpus
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
      <header className={styles.header}>
        <a href="/" className={`${styles.backBtn} btn-ghost`}>
          <Svg icon="arrowL" size={14} col={C.sec} sw={1.8} />
          <span>Exit</span>
        </a>
        <div className={styles.headerDivider} />
        <Wordmark />
        <span className={styles.headerLabel}>
          Mock Exam
        </span>

        {/* Timer */}
        <div className={styles.headerRight}>
          <div className={styles.timerBox}>
            <Svg icon="clock" size={13} col={C.mid} sw={2} />
            <span className={styles.timerValue}>
              {formatMSS(elapsedMs)}
            </span>
          </div>

          {/* Answered count */}
          <div className={styles.answeredCount}>
            <span className={styles.answeredCountNum}>
              {answeredCount}
            </span>
            <span className={styles.answeredCountTotal}>
              {" "}/ {total}
            </span>
          </div>

          <button
            onClick={submitExam}
            disabled={submitting}
            className={`${styles.submitBtn} btn-primary`}
            style={{ opacity: submitting ? 0.7 : 1 }}
          >
            <Svg icon="check" size={13} col="#fff" sw={2.5} />
            {submitting ? "Grading…" : "Submit Exam"}
          </button>
        </div>

        {/* Thin progress stripe */}
        <div className={styles.headerStripe}>
          <div
            className={styles.headerStripeFill}
            style={{
              width: `${total ? (answeredCount / total) * 100 : 0}%`,
              background: C.mid,
            }}
          />
        </div>
      </header>

      {/* ── Main layout ── */}
      <div className={styles.examLayout}>
        {/* ══ LEFT: Question pane ══ */}
        <div className={styles.questionPane}>
          {/* Mobile sidebar toggle */}
          <button
            className={styles.sidebarToggle}
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <Svg icon="chevD" size={14} col={C.sec} sw={2} style={{ transform: sidebarOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
            {sidebarOpen ? "Hide progress" : "Show progress & jump"}
          </button>

          {/* Question navigator grid */}
          {(list?.length ?? 0) > 0 && (
            <div className={styles.questionNav}>
              {list!.map((q, i) => {
                const a = ans[q.id];
                const cur = i === idx;
                return (
                  <button
                    key={q.id}
                    onClick={() => setIdx(i)}
                    className={`q-num-btn ${styles.qNumBtn}`}
                    style={{
                      borderColor: cur ? C.mid : a ? C.liteb : C.bdr,
                      background: a ? C.lite : C.surf,
                      color: a ? C.mid : cur ? C.mid : C.ter,
                      fontWeight: cur ? 700 : 500,
                      boxShadow: cur ? `0 0 0 3px ${C.lite}` : "none",
                    }}
                  >
                    {i + 1}
                  </button>
                );
              })}
            </div>
          )}

          {!list && !loadError && <LoadingState />}
          {loadError && (
            <ErrorState msg={loadError} onRetry={() => { setPhase("intro"); setLoadError(null); }} />
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
            <div className={styles.navButtons}>
              <button
                onClick={() => idx > 0 && setIdx((i) => i - 1)}
                className={`nav-btn ${styles.navButton} ${idx === 0 ? styles.navButtonDisabled : ""}`}
                disabled={idx === 0}
              >
                <Svg icon="chevL" size={13} col="currentColor" sw={2} />
                Previous
              </button>
              <button
                onClick={() => idx < total - 1 && setIdx((i) => i + 1)}
                className={`nav-btn ${styles.navButton} ${idx === total - 1 ? styles.navButtonDisabled : ""}`}
                disabled={idx === total - 1}
              >
                Next
                <Svg icon="chevR" size={13} col="currentColor" sw={2} />
              </button>

              {idx === total - 1 && (
                <button
                  onClick={submitExam}
                  disabled={submitting}
                  className={`${styles.submitBtn} btn-primary`}
                  style={{ marginLeft: "auto", opacity: submitting ? 0.7 : 1 }}
                >
                  <Svg icon="check" size={13} col="#fff" sw={2.5} />
                  {submitting ? "Grading…" : "Submit Exam"}
                </button>
              )}
            </div>
          )}
        </div>

        {/* ══ RIGHT: Sidebar ══ */}
        <div className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : ""}`}>
          {/* Answered progress */}
          <div className={styles.sidebarCard} style={{ boxShadow: SH.card }}>
            <Label col={C.ter} mb={10}>Exam Progress</Label>
            <div className={styles.progressSummary}>
              <span className={styles.progressNum}>{answeredCount}</span>
              <span className={styles.progressLabel}>of {total} answered</span>
            </div>
            <ProgressBar pct={total ? (answeredCount / total) * 100 : 0} color={C.mid} h={4} />
            <div className={styles.progressRow}>
              <span>
                Remaining:{" "}
                <span style={{ fontFamily: '"JetBrains Mono",monospace', fontWeight: 700, color: C.sec }}>
                  {total - answeredCount}
                </span>
              </span>
              <span>
                Time:{" "}
                <span style={{ fontFamily: '"JetBrains Mono",monospace', fontWeight: 700, color: C.mid }}>
                  {formatMSS(elapsedMs)}
                </span>
              </span>
            </div>
          </div>

          {/* Unanswered list */}
          <div className={styles.sidebarCard} style={{ boxShadow: SH.card }}>
            <Label col={C.ter} mb={10}>Jump to question</Label>
            <div className={styles.jumpGrid}>
              {(list ?? []).map((q, i) => {
                const a = ans[q.id];
                const cur = i === idx;
                return (
                  <button
                    key={q.id}
                    onClick={() => setIdx(i)}
                    className={styles.jumpBtn}
                    style={{
                      borderColor: cur ? C.mid : a ? C.liteb : C.bdr,
                      background: a ? C.lite : C.surf,
                      color: a ? C.mid : C.ter,
                      fontWeight: a ? 700 : 500,
                    }}
                  >
                    {i + 1}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Exam info */}
          <div className={styles.examInfo}>
            <Svg icon="info" size={14} col={C.mid} sw={2} />
            <div className={styles.examInfoText}>
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
      <div className={styles.metaRow}>
        <Pill bg={C.lite} col={C.mid} bdr={C.liteb}>{subject}</Pill>
        <Pill bg={dm.bg} col={dm.col} bdr={dm.bdr}>{diff}</Pill>
        {topic && <Pill bg={C.alt} col={C.sec} bdr={C.bdr}>{topic}</Pill>}
        {question.year && <Pill bg={C.alt} col={C.ter} bdr={C.bdr}>{question.year}</Pill>}
        <div className={styles.questionId}>{question.id}</div>
      </div>

      {/* Question card */}
      <QuestionCard style={{ marginBottom: "0.875rem" }}>
        <div className={styles.questionCardHeader}>
          <Label col={C.ter}>Question {index + 1} of {total}</Label>
          <Pill bg={dm.bg} col={dm.col} bdr={dm.bdr}>{diff}</Pill>
        </div>
        <MathText as="p" style={{ margin: 0, fontSize: "0.9375rem", lineHeight: 1.85, color: C.text, fontWeight: 400 }}>
          {question.question_text}
        </MathText>

        {question.question_images.length > 0 && (
          <div className={styles.questionImages}>
            {question.question_images.map((img) => (
              <img key={img} src={imageUrl(img)} alt={img} style={{ maxWidth: "100%", borderRadius: 8, border: `1px solid ${C.bdr}`, background: C.surf }} loading="lazy" />
            ))}
          </div>
        )}
      </QuestionCard>

      {/* Options — no feedback styling, just selection state */}
      <div className={styles.optionsList}>
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
              className={`opt-btn ${styles.mockOption}`}
              style={{
                borderColor: selected ? C.mid : isHov ? C.liteb : C.bdr,
                background: selected ? C.lite : isHov ? C.alt : C.surf,
              }}
            >
              <span
                className={styles.mockOptionLetter}
                style={{
                  background: selected ? C.mid : isHov ? C.mid : C.alt,
                  color: selected || isHov ? "#fff" : C.sec,
                }}
              >
                {l}
              </span>
              <span
                className={styles.mockOptionText}
                style={{ color: C.text, fontWeight: selected ? 500 : 400 }}
              >
                <MathText>{text}</MathText>
                {i < 9 && (
                  <span className={styles.mockOptionHint}>[{i + 1}]</span>
                )}
              </span>
              {selected && (
                <div className={styles.mockOptionCheck} style={{ background: C.mid }}>
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
  const correctCount = questions.filter((q) => graded[q.id]?.correct).length;
  const unanswered = questions.filter((q) => !ans[q.id]).length;
  const pct = total > 0 ? Math.round((correctCount / total) * 100) : 0;

  // Per-subject breakdown.
  const bySubject = new Map<string, { answered: number; correct: number }>();
  for (const q of questions) {
    const key = deriveSubject(q);
    const e = bySubject.get(key) ?? { answered: 0, correct: 0 };
    e.answered++;
    if (graded[q.id]?.correct) e.correct++;
    bySubject.set(key, e);
  }
  const subjectRows = Array.from(bySubject.entries())
    .map(([k, v]) => ({
      subject: k, answered: v.answered, correct: v.correct,
      pct: v.answered > 0 ? Math.round((v.correct / v.answered) * 100) : 0,
    }))
    .sort((a, b) => b.pct - a.pct);

  const avgPerQ = total > 0
    ? Math.round(questions.reduce((s, q) => s + (perQuestionMs[q.id] ?? 0), 0) / total)
    : 0;

  const toggleReveal = (qid: string) => {
    setRevealedQids((prev) => {
      const next = new Set(prev);
      if (next.has(qid)) next.delete(qid);
      else next.add(qid);
      return next;
    });
  };

  const headline = pct >= 80 ? "Outstanding work" : pct >= 60 ? "Strong performance" : pct >= 40 ? "Keep going" : "Needs attention";

  return (
    <Shell>
      <header className={styles.header}>
        <a href="/" className={`${styles.backBtn} btn-ghost`}>
          <Svg icon="arrowL" size={14} col={C.sec} sw={1.8} />
          <span>Dashboard</span>
        </a>
        <div className={styles.headerDivider} />
        <Wordmark />
        <span className={styles.headerLabel}>Mock Exam Results</span>
        <div className={styles.headerRight}>
          <a href="/practice" className={`${styles.backBtn} btn-ghost`}>
            <Svg icon="bolt" size={12} col={C.sec} sw={2} />
            Practice
          </a>
          <button onClick={onRestart} className={`${styles.submitBtn} btn-primary`} style={{ background: C.mid }}>
            <Svg icon="play" size={12} col="#fff" sw={2.5} />
            New Exam
          </button>
        </div>
      </header>

      <div className={styles.resultsWrapper}>
        {/* ── Headline ── */}
        <div className={styles.resultsHeadline} style={{ boxShadow: SH.card }}>
          <div className={styles.resultsCircle} style={{
            borderColor: pct >= 70 ? C.green : pct >= 50 ? C.amber : C.red,
          }}>
            <span className={styles.resultsCirclePct} style={{
              color: pct >= 70 ? C.green : pct >= 50 ? C.amber : C.red,
            }}>
              {pct}%
            </span>
            <span className={styles.resultsCircleLabel}>Score</span>
          </div>
          <div className={styles.resultsHeadlineBody}>
            <h1 className={styles.resultsTitle}>{headline}</h1>
            <div className={styles.resultsStats}>
              <span>
                <span style={{ fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, color: C.green }}>
                  {correctCount}
                </span>{" "}correct
              </span>
              <span>
                <span style={{ fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, color: C.red }}>
                  {total - correctCount - unanswered}
                </span>{" "}incorrect
              </span>
              {unanswered > 0 && (
                <span>
                  <span style={{ fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, color: C.ter }}>
                    {unanswered}
                  </span>{" "}blank
                </span>
              )}
              <span>
                <Svg icon="clock" size={11} col={C.ter} sw={2} />
                <span style={{ fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, color: C.mid, marginLeft: 4 }}>
                  {formatMSS(elapsedMs)}
                </span>{" "}total
              </span>
              <span>
                <span style={{ fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, color: C.sec }}>
                  {formatMSS(avgPerQ)}
                </span>{" "}avg/Q
              </span>
            </div>
          </div>
        </div>

        {/* ── Per-question result grid ── */}
        <div className={styles.resultsPerQuestion} style={{ boxShadow: SH.card }}>
          <Label col={C.ter} mb={12}>Per-question breakdown — click to reveal solution</Label>
          <div className={styles.resultsQuestionGrid}>
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
                    document.getElementById(`q-${q.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
                    toggleReveal(q.id);
                  }}
                  className={styles.resultsQBtn}
                  style={{ background: bg, border: `1.5px solid ${bdr}`, color: col }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.transform = "scale(1.08)"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.transform = "scale(1)"; }}
                  title={`Q${i + 1}: ${blank ? "No answer" : ok ? "Correct" : "Incorrect"}`}
                >
                  {i + 1}
                </div>
              );
            })}
          </div>

          {/* Per-subject table */}
          <div className={styles.subjectTable}>
            {subjectRows.map((r) => {
              const col = r.pct >= 70 ? C.green : r.pct >= 50 ? C.amber : C.red;
              return (
                <div key={r.subject}>
                  <div className={styles.subjectTableRow}>
                    <span>{r.subject}</span>
                    <span style={{ fontFamily: '"JetBrains Mono", monospace', color: col }}>
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
        <div className={styles.resultsReviewList}>
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
              <div key={q.id} id={`q-${q.id}`} className={styles.resultsReviewCard} style={{ boxShadow: SH.card }}>
                {/* Result header */}
                <div className={styles.resultsReviewHeader} style={{ background: bg, borderBottom: revealed ? `1px solid ${C.bdr}` : "none" }}>
                  <div className={styles.resultsReviewNum} style={{ background: col }}>{i + 1}</div>
                  <div className={styles.resultsReviewBody2}>
                    <div className={styles.resultsReviewSubject}>
                      {deriveSubject(q)}{q.year ? ` · ${q.year}` : ""}
                    </div>
                    <div className={styles.resultsReviewMeta}>
                      Your answer: <span style={{ color: blank ? C.ter : col, fontWeight: 700 }}>{userAns ?? "—"}</span>
                      {"  ·  "}Correct: <span style={{ color: C.green, fontWeight: 700 }}>{g?.correct_answer ?? "?"}</span>
                      {perQuestionMs[q.id] ? <>{"  ·  "}{formatMSS(perQuestionMs[q.id])}</> : null}
                    </div>
                  </div>
                  <button
                    onClick={() => toggleReveal(q.id)}
                    className={styles.resultsRevealBtn}
                    style={{ borderColor: bdr, color: col }}
                  >
                    <Svg icon={revealed ? "eye" : "book"} size={12} col={col} sw={2} />
                    {revealed ? "Hide solution" : "Show solution"}
                  </button>
                </div>

                {/* Question body */}
                <div className={styles.resultsReviewBody} style={{ display: revealed ? "block" : "none" }}>
                  <MathText as="p" style={{ margin: "0 0 0.875rem 0", fontSize: "0.9375rem", lineHeight: 1.85, color: C.text }}>
                    {q.question_text}
                  </MathText>

                  {q.question_images.length > 0 && (
                    <div className={styles.reviewImages}>
                      {q.question_images.map((img) => (
                        <img key={img} src={imageUrl(img)} alt={img} style={{ maxWidth: "100%", borderRadius: 8, border: `1px solid ${C.bdr}` }} loading="lazy" />
                      ))}
                    </div>
                  )}

                  {/* Options with correct/incorrect highlight */}
                  <div className={styles.resultsOptionsList}>
                    {Object.keys(q.options).sort().map((l) => {
                      const isCorrect = l === g?.correct_answer;
                      const isUserPick = l === userAns;
                      const bgC = isCorrect ? C.gLite : isUserPick ? C.rLite : C.surf;
                      const bdrC = isCorrect ? C.green : isUserPick ? C.red : C.bdr;
                      const lblBg = isCorrect ? C.green : isUserPick ? C.red : C.alt;
                      const lblCol = isCorrect || isUserPick ? "#fff" : C.sec;
                      return (
                        <div key={l} className={styles.resultsOptionRow} style={{ background: bgC, borderColor: bdrC }}>
                          <span className={styles.resultsOptionLetter} style={{ background: lblBg, color: lblCol }}>{l}</span>
                          <span className={styles.resultsOptionText}>
                            <MathText>{q.options[l]}</MathText>
                          </span>
                          {isCorrect && <Svg icon="check" size={12} col={C.green} sw={2.5} />}
                        </div>
                      );
                    })}
                  </div>

                  {/* Solution */}
                  {g?.explanation || g?.enrichment?.markdown ? (
                    <div>
                      {g.enrichment?.markdown ? (
                        <MathText as="div" style={{ color: C.text, fontSize: "0.875rem", lineHeight: 1.9, whiteSpace: "pre-wrap" }}>
                          {g.enrichment.markdown}
                        </MathText>
                      ) : (
                        <MathText as="p" style={{ margin: 0, color: C.text, fontSize: "0.875rem", lineHeight: 1.9, whiteSpace: "pre-wrap" }}>
                          {g.explanation}
                        </MathText>
                      )}
                    </div>
                  ) : (
                    <div style={{ fontSize: "0.75rem", color: C.ter, fontStyle: "italic" }}>
                      No worked solution available for this question.
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom CTAs */}
        <div className={styles.resultsBottomActions}>
          <button onClick={onRestart} className={`${styles.resultsBottomBtn} btn-primary`} style={{ boxShadow: SH.blue }}>
            <Svg icon="play" size={13} col="#fff" sw={2.5} />
            Take Another Exam
          </button>
          <a href="/" className={`${styles.resultsBottomLink} btn-ghost`}>
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
    <div className={styles.page}>
      {children}
    </div>
  );
}

function LoadingState() {
  return (
    <div className={styles.loadingState} style={{ boxShadow: SH.card }}>
      <div className={`${styles.loadingDot} pulse-dot`} />
      <div style={{ color: C.sec, fontSize: "0.875rem" }}>Loading questions…</div>
    </div>
  );
}

function ErrorState({ msg, onRetry }: { msg: string; onRetry: () => void }) {
  return (
    <div className={styles.errorState}>
      <div className={styles.errorMsg}>{msg}</div>
      <button onClick={onRetry} className={styles.errorRetryBtn}>Back</button>
    </div>
  );
}
