"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { C, SH, SESSION, DIFF_META } from "@/lib/constants";
import type { Question as DbQuestion, Enrichment } from "@/lib/db";
import { recordAttempt, MODULE_LABELS, RADAR_AXIS_ORDER } from "@/lib/progress";
import { Svg } from "@/components/icons";
import { Bar, Pill, KBD, Wordmark, Label } from "@/components/atoms";
import { ProgressBar } from "@/components/ProgressBar";
import { QuestionView } from "@/components/QuestionView";

/**
 * PracticeHub — the real-data practice session page (ESA-8).
 *
 * Replaces the MOCK_QUESTIONS prototype with real DB-backed questions:
 *   - Loads SESSION (=10) random questions on mount and whenever the user
 *     changes the exam filter or requests a new session.
 *   - Two-stage reveal: questions are first fetched with reveal=false so the
 *     correct answer never ships to the browser until the user has answered.
 *     On first answer for a given question, we fetch /api/questions/{id}
 *     with reveal=true and patch the local copy.
 *   - Keyboard shortcuts: 1-9 / a-i select option, S toggles solution,
 *     arrows navigate between questions.
 *
 * Session state is owned here and passed down to <QuestionView>.
 */

type StatsResp = {
  total_questions: number;
  by_exam: Record<
    string,
    { count: number; years: string[]; modules: string[] }
  >;
};

const EXAM_LABELS: Record<string, string> = {
  esat: "ESAT",
  engaa: "ENGAA (legacy)",
  nsaa: "NSAA (legacy)",
  tmua: "TMUA (legacy)",
};

function prettyExam(k: string): string {
  return EXAM_LABELS[k] ?? k.toUpperCase();
}

export default function PracticeHub() {
  // Session data
  const [questions, setQuestions] = useState<DbQuestion[] | null>(null);
  const [revealedById, setRevealedById] = useState<Record<string, DbQuestion>>(
    {}
  );
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filterExam, setFilterExam] = useState<string>(""); // "" = any
  const [filterModule, setFilterModule] = useState<string>(""); // "" = any
  const [filterDifficulty, setFilterDifficulty] = useState<string>(""); // "" = any

  // Session interaction state
  const [idx, setIdx] = useState(0);
  const [ans, setAns] = useState<Record<string, string>>({}); // qid -> letter
  const ansRef = useRef<Record<string, string>>({});
  const [showSolnFor, setShowSolnFor] = useState<Record<string, boolean>>({});
  const [hovOpt, setHovOpt] = useState<string | null>(null);

  // Corpus stats for the sidebar
  const [stats, setStats] = useState<StatsResp | null>(null);

  // Stale-fetch guard
  const fetchIdRef = useRef(0);

  useEffect(() => {
    ansRef.current = ans;
  }, [ans]);

  // Load corpus stats once for the sidebar / filter dropdown.
  useEffect(() => {
    let cancelled = false;
    fetch("/api/questions/stats")
      .then((r) => r.json())
      .then((s: StatsResp) => {
        if (!cancelled) setStats(s);
      })
      .catch(() => {
        /* sidebar is non-critical; leave as null */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load a fresh session of random questions whenever the filter changes
  // or the user requests a new session.
  const loadSession = useCallback(
    (exam: string, module: string, difficulty: string) => {
      const myId = ++fetchIdRef.current;
      setQuestions(null);
      setLoadError(null);
      setAns({});
      ansRef.current = {};
      setShowSolnFor({});
      setIdx(0);
      setHovOpt(null);
      setRevealedById({});

      const url = new URL("/api/questions/random", window.location.origin);
      url.searchParams.set("count", String(SESSION));
      url.searchParams.set("reveal", "false");
      if (exam) url.searchParams.set("exam_type", exam);
      if (module) url.searchParams.set("module", module);
      if (difficulty) url.searchParams.set("difficulty", difficulty);

      fetch(url.toString())
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then(
          (data: { questions: DbQuestion[]; total_available: number }) => {
            if (myId !== fetchIdRef.current) return; // stale
            if (!data.questions || data.questions.length === 0) {
              setLoadError("No questions match this filter.");
              return;
            }
            setQuestions(data.questions);
          }
        )
        .catch((e: Error) => {
          if (myId !== fetchIdRef.current) return;
          setLoadError(e.message || "Failed to load questions.");
        });
    },
    []
  );

  // Sync the active filters into the URL so sessions are shareable and the
  // dashboard's deep-links (e.g. /practice?module=physics) keep working on
  // refresh / browser-back.
  const syncUrl = useCallback(
    (exam: string, module: string, difficulty: string) => {
      if (typeof window === "undefined") return;
      const u = new URL(window.location.href);
      u.searchParams.delete("exam_type");
      u.searchParams.delete("module");
      u.searchParams.delete("difficulty");
      if (exam) u.searchParams.set("exam_type", exam);
      if (module) u.searchParams.set("module", module);
      if (difficulty) u.searchParams.set("difficulty", difficulty);
      window.history.replaceState(null, "", u.toString());
    },
    []
  );

  // Seed filters from the URL on first mount so deep-links from the
  // dashboard Knowledge Map land on a pre-filtered session.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const sp = new URL(window.location.href).searchParams;
    const e = sp.get("exam_type") ?? "";
    const m = sp.get("module") ?? "";
    const d = sp.get("difficulty") ?? "";
    if (e) setFilterExam(e);
    if (m) setFilterModule(m);
    if (d) setFilterDifficulty(d);
    // Only run once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Initial load + reload on any filter change.
  useEffect(() => {
    loadSession(filterExam, filterModule, filterDifficulty);
    syncUrl(filterExam, filterModule, filterDifficulty);
  }, [filterExam, filterModule, filterDifficulty, loadSession, syncUrl]);

  // Submit the chosen answer to the scoring endpoint on first answer.
  // The server records the attempt and returns correctness + worked
  // solution. The local copy is then patched with those fields so the
  // UI can render feedback (correct/incorrect colour, solution panel).
  const submitAnswer = useCallback(
    (qid: string, letter: string) => {
      if (revealedById[qid]) return;
      const localQuestion = questions?.find((q) => q.id === qid);
      fetch(`/api/questions/${encodeURIComponent(qid)}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: letter }),
      })
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then(
          (scored: Pick<
            DbQuestion,
            "correct_answer" | "explanation" | "explanation_images" | "enrichment"
          > & { correct: boolean }) => {
            // Record into the client-side progress log so the dashboard's
            // stats / Knowledge Map reflect real practice history.
            if (localQuestion) {
              recordAttempt({
                questionId: qid,
                examType: localQuestion.exam_type,
                module: localQuestion.module ?? "",
                correct: scored.correct,
              });
            }
            setRevealedById((prev) => ({
              ...prev,
              [qid]: {
                ...(localQuestion ?? ({} as DbQuestion)),
                correct_answer: scored.correct_answer,
                explanation: scored.explanation ?? "",
                explanation_images: scored.explanation_images ?? [],
                enrichment: scored.enrichment ?? null,
              },
            }));
          }
        )
        .catch(() => {
          /* leave unscored; UI falls back gracefully */
        });
    },
    [revealedById, questions]
  );

  const pick = useCallback(
    (letter: string) => {
      const list = questions;
      if (!list) return;
      const qid = list[idx]?.id;
      if (!qid) return;
      if (ansRef.current[qid]) return; // locked
      ansRef.current[qid] = letter;
      setAns((prev) => ({ ...prev, [qid]: letter }));
      submitAnswer(qid, letter);
    },
    [idx, questions, submitAnswer]
  );

  // Keyboard shortcuts
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target &&
        ["SELECT", "INPUT", "TEXTAREA"].includes(target.tagName)
      )
        return;
      const list = questions;
      if (!list) return;
      const qid = list[idx]?.id;
      const k = e.key;

      // 1-9 -> option letters A-I (capped to actual option count)
      if (/^[1-9]$/.test(k)) {
        const letterIdx = parseInt(k, 10) - 1;
        const opts = Object.keys(list[idx]?.options ?? {}).sort();
        if (letterIdx < opts.length) pick(opts[letterIdx]);
        return;
      }
      // a-i -> option letter (uppercase)
      if (/^[a-i]$/i.test(k)) {
        const L = k.toUpperCase();
        if (list[idx]?.options?.[L]) pick(L);
        return;
      }
      if ((k === "s" || k === "S") && ansRef.current[qid]) {
        setShowSolnFor((prev) => ({ ...prev, [qid]: !prev[qid] }));
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
  }, [idx, questions, pick, submitAnswer]);

  // ── Derived state ──
  const list = questions;
  const total = list?.length ?? SESSION;
  const current = list?.[idx];
  const currentRevealed = current ? revealedById[current.id] ?? current : null;
  const chosen = current ? ans[current.id] ?? null : null;
  const doneCount = list ? Object.keys(ans).filter((k) => list.some((q) => q.id === k)).length : 0;
  const rightCount = list
    ? Object.entries(ans).filter(([qid, letter]) => {
        const revealed = revealedById[qid];
        return !!revealed && revealed.correct_answer === letter;
      }).length
    : 0;

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
      {/* ── Header ── */}
      <header
        className="header-padding"
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

        {/* Keyboard legend */}
        <div
          className="kbd-legend"
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: C.alt,
            borderRadius: 8,
            padding: "5px 10px",
          }}
        >
          <Svg icon="bolt" size={12} col={C.ter} sw={1.8} />
          {[
            { k: "1\u20139", label: "Select" },
            { k: "S", label: "Solution" },
          ].map(({ k, label }, i) => (
            <span key={k} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              {i > 0 && (
                <span style={{ color: C.bdr2, fontSize: "0.75rem" }}>&middot;</span>
              )}
              <KBD>{k}</KBD>
              <span style={{ fontSize: "0.6875rem", color: C.ter }}>{label}</span>
            </span>
          ))}
          <span style={{ color: C.bdr2, fontSize: "0.75rem" }}>&middot;</span>
          <KBD>&larr;</KBD>
          <KBD>&rarr;</KBD>
          <span style={{ fontSize: "0.6875rem", color: C.ter }}>Navigate</span>
        </div>

        {/* Session dots */}
        <div className="session-dots" style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <div style={{ display: "flex", gap: 3 }}>
            {(list ?? []).map((q, i) => {
              const a = ans[q.id];
              const revealed = revealedById[q.id];
              const ok = !!(a && revealed && revealed.correct_answer === a);
              return (
                <div
                  key={q.id}
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: !a
                      ? i === idx ? C.mid : C.bdr
                      : ok ? C.green : C.red,
                    transition: "background 0.25s",
                    opacity: i === idx && !a ? 1 : undefined,
                    boxShadow: i === idx && !a ? `0 0 0 2px ${C.liteb}` : undefined,
                  }}
                />
              );
            })}
          </div>
          <div style={{ fontSize: "0.8125rem", color: C.sec }}>
            <span
              style={{
                fontFamily: '"JetBrains Mono",monospace',
                fontWeight: 700,
                color: C.text,
              }}
            >
              {doneCount}
            </span>
            <span style={{ color: C.ter }}> / {total}</span>
          </div>
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
              width: `${total ? (doneCount / total) * 100 : 0}%`,
              background: doneCount === total && total > 0 ? C.green : C.mid,
              transition: "width 0.45s cubic-bezier(0.16,1,0.3,1), background 0.3s",
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
                const revealed = revealedById[q.id];
                const ok = !!(a && revealed && revealed.correct_answer === a);
                const cur = i === idx;
                let bg: string = C.surf,
                  bdr: string = C.bdr,
                  col: string = C.ter;
                if (a) {
                  bg = ok ? C.gLite : C.rLite;
                  bdr = ok ? C.green : C.red;
                  col = ok ? C.green : C.red;
                }
                if (cur) bdr = C.mid;
                return (
                  <button
                    key={q.id}
                    onClick={() => setIdx(i)}
                    className="q-num-btn"
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 8,
                      border: `2px solid ${bdr}`,
                      background: bg,
                      color: col,
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
                    {a ? (
                      <svg
                        width="11"
                        height="11"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke={col}
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        {ok ? (
                          <path d="M4.5 12.75l6 6 9-13.5" />
                        ) : (
                          <>
                            <path d="M6 18 18 6" />
                            <path d="M6 6l12 12" />
                          </>
                        )}
                      </svg>
                    ) : (
                      i + 1
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* Loading / error / question */}
          {!list && !loadError && <LoadingState />}
          {loadError && <ErrorState msg={loadError} onRetry={() => loadSession(filterExam, filterModule, filterDifficulty)} />}
          {list && list.length === 0 && (
            <ErrorState msg="No questions available." onRetry={() => loadSession(filterExam, filterModule, filterDifficulty)} />
          )}

          {current && currentRevealed && (
            <QuestionView
              question={currentRevealed}
              index={idx}
              total={total}
              chosen={chosen}
              onChoose={pick}
              showSolution={!!showSolnFor[current.id]}
              onToggleSolution={(next) =>
                setShowSolnFor((prev) => ({ ...prev, [current.id]: next }))
              }
              hovOpt={hovOpt}
              onHoverOption={setHovOpt}
            />
          )}

          {/* Session complete */}
          {list && doneCount === list.length && list.length > 0 && (
            <SessionComplete
              right={rightCount}
              total={total}
              questions={list}
              ans={ans}
              revealedById={revealedById}
              onJump={setIdx}
            />
          )}

          {/* Prev / Next */}
          {list && list.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
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
            </div>
          )}
        </div>

        {/* ══ RIGHT: Sidebar ══ */}
        <div className="practice-sidebar" style={{ width: 268, flexShrink: 0 }}>
          {/* Exam filter + new session */}
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
            <Label col={C.ter} mb={8}>
              Exam
            </Label>
            <select
              value={filterExam}
              onChange={(e) => setFilterExam(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                border: `1px solid ${C.bdr}`,
                borderRadius: 8,
                background: C.surf,
                color: C.text,
                fontSize: "0.8125rem",
                fontWeight: 500,
                fontFamily: "Inter, sans-serif",
                cursor: "pointer",
                boxSizing: "border-box",
              }}
            >
              <option value="">Any exam</option>
              {stats &&
                Object.keys(stats.by_exam)
                  .sort()
                  .map((k) => (
                    <option key={k} value={k}>
                      {prettyExam(k)} ({stats.by_exam[k].count})
                    </option>
                  ))}
            </select>

            <Label col={C.ter} mb={8} mt={12}>
              Subject
            </Label>
            <select
              value={filterModule}
              onChange={(e) => setFilterModule(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                border: `1px solid ${C.bdr}`,
                borderRadius: 8,
                background: C.surf,
                color: C.text,
                fontSize: "0.8125rem",
                fontWeight: 500,
                fontFamily: "Inter, sans-serif",
                cursor: "pointer",
                boxSizing: "border-box",
              }}
            >
              <option value="">Any subject</option>
              {RADAR_AXIS_ORDER.map((code) => (
                <option key={code} value={code}>
                  {MODULE_LABELS[code] ?? code}
                </option>
              ))}
            </select>

            <Label col={C.ter} mb={8} mt={12}>
              Difficulty
            </Label>
            <select
              value={filterDifficulty}
              onChange={(e) => setFilterDifficulty(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                border: `1px solid ${C.bdr}`,
                borderRadius: 8,
                background: C.surf,
                color: C.text,
                fontSize: "0.8125rem",
                fontWeight: 500,
                fontFamily: "Inter, sans-serif",
                cursor: "pointer",
                boxSizing: "border-box",
              }}
            >
              <option value="">Any difficulty</option>
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
              <option value="Very Hard">Very Hard</option>
            </select>

            {(filterExam || filterModule || filterDifficulty) && (
              <button
                onClick={() => {
                  setFilterExam("");
                  setFilterModule("");
                  setFilterDifficulty("");
                }}
                className="btn-ghost"
                style={{
                  marginTop: 8,
                  background: "none",
                  border: "none",
                  color: C.sec,
                  fontSize: "0.75rem",
                  fontWeight: 500,
                  fontFamily: "Inter, sans-serif",
                  cursor: "pointer",
                  padding: "4px 0",
                  textAlign: "left",
                }}
              >
                Clear filters
              </button>
            )}

            <button
              onClick={() => loadSession(filterExam, filterModule, filterDifficulty)}
              className="btn-primary"
              style={{
                marginTop: 10,
                width: "100%",
                padding: "8px 12px",
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
                justifyContent: "center",
                gap: 6,
              }}
            >
              <Svg icon="bolt" size={12} col="#fff" sw={2} />
              New session
            </button>
          </div>

          {/* Practising now */}
          <div
            style={{
              background: C.lite,
              border: `1px solid ${C.liteb}`,
              borderRadius: 12,
              padding: "10px 14px",
              marginBottom: 12,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: C.mid,
                flexShrink: 0,
              }}
              className="pulse-dot"
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: "0.6875rem",
                  fontWeight: 600,
                  color: C.ter,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  marginBottom: 1,
                }}
              >
                Practising now
              </div>
              <div
                style={{
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  color: C.mid,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {current
                  ? `${prettyExam(current.exam_type)}${current.year ? ` ${current.year}` : ""}`
                  : "Loading..."}
              </div>
            </div>
          </div>

          {/* Session progress */}
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
              Session Progress
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
                {doneCount}
              </span>
              <span style={{ fontSize: "0.875rem", color: C.ter }}>
                of {total} answered
              </span>
            </div>
            <ProgressBar
              pct={total ? (doneCount / total) * 100 : 0}
              color={doneCount === total && total > 0 ? C.green : C.mid}
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
                Correct:{" "}
                <span
                  style={{
                    fontFamily: '"JetBrains Mono",monospace',
                    fontWeight: 700,
                    color: C.green,
                  }}
                >
                  {rightCount}
                </span>
              </span>
              <span>
                Remaining:{" "}
                <span
                  style={{
                    fontFamily: '"JetBrains Mono",monospace',
                    fontWeight: 700,
                    color: C.sec,
                  }}
                >
                  {total - doneCount}
                </span>
              </span>
            </div>
          </div>

          {/* Corpus stats */}
          {stats && (
            <div
              style={{
                background: C.surf,
                border: `1px solid ${C.bdr}`,
                borderRadius: 12,
                padding: "1.1rem 1.2rem",
                boxShadow: SH.card,
              }}
            >
              <Label col={C.ter} mb={10}>
                Corpus
              </Label>
              <div
                style={{
                  fontSize: "0.6875rem",
                  color: C.ter,
                  marginBottom: 8,
                  fontFamily: '"JetBrains Mono", monospace',
                }}
              >
                {stats.total_questions.toLocaleString()} questions
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {Object.entries(stats.by_exam)
                  .sort((a, b) => b[1].count - a[1].count)
                  .map(([k, info]) => {
                    const pct = Math.round(
                      (info.count / stats.total_questions) * 100
                    );
                    return (
                      <div key={k}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            fontSize: "0.75rem",
                            color: C.sec,
                            marginBottom: 3,
                          }}
                        >
                          <span>{prettyExam(k)}</span>
                          <span
                            style={{
                              fontFamily: '"JetBrains Mono", monospace',
                              color: C.ter,
                            }}
                          >
                            {info.count}
                          </span>
                        </div>
                        <Bar pct={pct} color={C.mid} />
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Helper components ──

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
      <div style={{ color: C.sec, fontSize: "0.875rem" }}>Loading questions…</div>
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
      <div style={{ color: C.red, fontSize: "0.9375rem", fontWeight: 600, marginBottom: 8 }}>
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
        Try again
      </button>
    </div>
  );
}

function SessionComplete({
  right,
  total,
  questions,
  ans,
  revealedById,
  onJump,
}: {
  right: number;
  total: number;
  questions: DbQuestion[];
  ans: Record<string, string>;
  revealedById: Record<string, DbQuestion>;
  onJump: (i: number) => void;
}) {
  return (
    <div
      style={{
        background: C.surf,
        border: `1px solid ${C.gBdr}`,
        borderRadius: 14,
        padding: "1.375rem 1.5rem",
        marginBottom: 8,
        marginTop: 8,
        boxShadow: SH.card,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 14,
          marginBottom: 14,
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: C.gLite,
            border: `1px solid ${C.gBdr}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <Svg icon="trophy" size={22} col={C.green} sw={1.5} />
        </div>
        <div style={{ flex: 1 }}>
          <div
            style={{
              fontWeight: 700,
              color: C.text,
              fontSize: "1rem",
              letterSpacing: "-0.01em",
              marginBottom: 3,
            }}
          >
            Session complete
          </div>
          <div style={{ fontSize: "0.875rem", color: C.sec }}>
            <span
              style={{
                fontFamily: '"JetBrains Mono",monospace',
                fontWeight: 700,
                color: right >= 8 ? C.green : right >= 5 ? C.amber : C.red,
              }}
            >
              {right}/{total}
            </span>{" "}
            correct &mdash;{" "}
            {right >= 8 ? "excellent work." : right >= 5 ? "solid session." : "keep practising."}
          </div>
        </div>
        <a
          href="/"
          className="btn-primary"
          style={{
            padding: "8px 16px",
            borderRadius: 8,
            border: "none",
            background: C.mid,
            color: "#fff",
            fontFamily: "Inter,sans-serif",
            fontWeight: 600,
            fontSize: "0.8125rem",
            flexShrink: 0,
            textDecoration: "none",
            display: "inline-flex",
            alignItems: "center",
          }}
        >
          Dashboard
        </a>
      </div>
      {/* Per-question result grid */}
      <div style={{ display: "flex", gap: 5 }}>
        {questions.map((q, i) => {
          const a = ans[q.id];
          const revealed = revealedById[q.id];
          const ok = !!(a && revealed && revealed.correct_answer === a);
          return (
            <div
              key={q.id}
              onClick={() => onJump(i)}
              style={{
                flex: 1,
                height: 28,
                borderRadius: 6,
                cursor: "pointer",
                background: ok ? C.gLite : C.rLite,
                border: `1px solid ${ok ? C.gBdr : C.rBdr}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <svg
                width="10"
                height="10"
                viewBox="0 0 24 24"
                fill="none"
                stroke={ok ? C.green : C.red}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {ok ? (
                  <path d="M4.5 12.75l6 6 9-13.5" />
                ) : (
                  <>
                    <path d="M6 18 18 6" />
                    <path d="M6 6l12 12" />
                  </>
                )}
              </svg>
            </div>
          );
        })}
      </div>
    </div>
  );
}
