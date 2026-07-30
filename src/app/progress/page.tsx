"use client";

import { useEffect, useMemo, useState } from "react";
import {
  C,
  SH,
  DAYS_LEFT,
} from "@/lib/constants";
import {
  loadProgress,
  computeStats,
  buildRadarData,
  formatMSS,
  clearProgress,
  type ProgressStats,
  type AttemptRecord,
} from "@/lib/progress";
import { Svg } from "@/components/icons";
import { Bar, Pill, Wordmark, NavPill } from "@/components/atoms";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { StatCard } from "@/components/StatCard";
import { RadarChartSVG } from "@/components/RadarChartSVG";

/**
 * ProgressPage — long-form analytics view (ESA-18 follow-up).
 *
 * Sibling to the dashboard. Where the dashboard is the daily "what next"
 * surface, this page is the reflective "how have I been doing" view:
 *   - Headline stats (streak, accuracy, total answered, best run)
 *   - Knowledge Map radar (per-module accuracy)
 *   - Per-module and per-exam breakdown tables
 *   - Recent activity log (last 15 attempts)
 *
 * All derived from the same `computeStats` source as the dashboard so the
 * two views never disagree. First-time users see an empty state that
 * links to /practice.
 */

type StatCardProps = {
  icon: Parameters<typeof StatCard>[0]["icon"];
  label: string;
  val: string;
  unit?: string;
  col: string;
  bg: string;
  delta: string;
  deltaCol: string;
};

function buildStatsCards(stats: ProgressStats): StatCardProps[] {
  const accuracyDelta =
    stats.accuracy >= 70 ? "strong" : stats.accuracy >= 50 ? "ok" : "keep going";
  const accuracyDeltaCol =
    stats.accuracy >= 70 ? C.green : stats.accuracy >= 50 ? C.amber : C.red;
  return [
    {
      icon: "flame",
      label: "Day Streak",
      val: String(stats.dayStreak),
      unit: stats.dayStreak === 1 ? "day" : "days",
      col: C.amber,
      bg: "#FFF7ED",
      delta:
        stats.activeDayCount === 1 ? "1 day" : `${stats.activeDayCount} days`,
      deltaCol: C.mid,
    },
    {
      icon: "trendUp",
      label: "Accuracy",
      val: String(stats.accuracy),
      unit: "%",
      col: accuracyDeltaCol,
      bg:
        stats.accuracy >= 70 ? C.gLite : stats.accuracy >= 50 ? C.aLite : C.rLite,
      delta: accuracyDelta,
      deltaCol: accuracyDeltaCol,
    },
    {
      icon: "sparkle",
      label: "Total Answered",
      val: String(stats.totalAnswered),
      unit: "questions",
      col: C.purp,
      bg: C.pLite,
      delta: `${stats.totalCorrect} ✓`,
      deltaCol: C.green,
    },
    {
      icon: "trophy",
      label: "Best Streak",
      val: String(stats.bestStreak),
      unit: stats.bestStreak === 1 ? "correct" : "correct",
      col: C.green,
      bg: C.gLite,
      delta:
        stats.currentStreak === stats.bestStreak && stats.bestStreak > 0
          ? "on run"
          : `now ${stats.currentStreak}`,
      deltaCol:
        stats.currentStreak === stats.bestStreak && stats.bestStreak > 0
          ? C.green
          : C.ter,
    },
  ];
}

/** Relative-time formatter for the recent-activity log ("2h ago"). */
function relativeTime(ts: number): string {
  const diffMs = Date.now() - ts;
  const sec = Math.round(diffMs / 1000);
  if (sec < 60) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 7) return `${day}d ago`;
  const wk = Math.round(day / 7);
  return wk === 1 ? "1w ago" : `${wk}w ago`;
}

const EXAM_LABELS: Record<string, string> = {
  esat: "ESAT",
  engaa: "ENGAA",
  nsaa: "NSAA",
  nsaa_s2: "NSAA S2",
  tmua: "TMUA",
};

function prettyExam(code: string): string {
  return EXAM_LABELS[code] ?? (code ? code.toUpperCase() : "General");
}

export default function ProgressPage() {
  const [stats, setStats] = useState<ProgressStats | null>(null);
  const [recent, setRecent] = useState<AttemptRecord[]>([]);
  const [resetOpen, setResetOpen] = useState(false);

  // Load progress in the browser (localStorage is SSR-absent).
  useEffect(() => {
    const refresh = () => {
      const s = loadProgress();
      setStats(computeStats(s));
      setRecent([...s.attempts].reverse().slice(0, 15));
    };
    refresh();
    const onStorage = (e: StorageEvent) => {
      if (e.key === "esat-progress-v1") refresh();
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const handleReset = () => {
    clearProgress();
    setResetOpen(false);
    const s = loadProgress();
    setStats(computeStats(s));
    setRecent([]);
  };

  const hasReal = !!(stats && stats.hasData);
  const radar = useMemo(
    () =>
      hasReal
        ? buildRadarData(stats!)
        : [
            { axis: "Maths 1", v: 0, answered: 0, code: "maths1" },
            { axis: "Physics", v: 0, answered: 0, code: "physics" },
            { axis: "Chemistry", v: 0, answered: 0, code: "chemistry" },
            { axis: "Biology", v: 0, answered: 0, code: "biology" },
            { axis: "Maths 2", v: 0, answered: 0, code: "maths2" },
          ],
    [hasReal, stats]
  );
  const radarAvg = radar.length
    ? Math.round(
        radar.filter((d) => d.answered > 0).reduce((s, d) => s + d.v, 0) /
          Math.max(1, radar.filter((d) => d.answered > 0).length)
      )
    : 0;

  if (!stats) {
    // SSR + first paint — render the shell so layout doesn't jump.
    return (
      <div style={{ fontFamily: "Inter, sans-serif", background: C.bg, minHeight: "100vh" }}>
        <Header activeProgress streak={0} />
        <main style={{ maxWidth: 1120, margin: "0 auto", padding: "2rem 2rem 3rem" }}>
          <div style={{ color: C.sec, fontSize: "0.875rem" }}>Loading…</div>
        </main>
      </div>
    );
  }

  const cards = buildStatsCards(stats);
  const totalDone = stats.totalAnswered;

  // Bucket the recent attempts by day for a tiny bar of the last 14 days.
  const last14 = useMemo(() => {
    const days: { key: string; label: string; count: number; correct: number }[] = [];
    const cursor = new Date();
    for (let i = 13; i >= 0; i--) {
      const d = new Date(cursor);
      d.setDate(d.getDate() - i);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
        d.getDate()
      ).padStart(2, "0")}`;
      days.push({
        key,
        label: d.toLocaleDateString(undefined, { weekday: "narrow" }),
        count: 0,
        correct: 0,
      });
    }
    const byKey = new Map(days.map((d) => [d.key, d]));
    // Pull the full attempt list (not just the 15 recent) for the chart.
    const all = loadProgress().attempts;
    for (const a of all) {
      const d = new Date(a.ts);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
        d.getDate()
      ).padStart(2, "0")}`;
      const bucket = byKey.get(key);
      if (!bucket) continue;
      bucket.count++;
      if (a.correct) bucket.correct++;
    }
    return days;
  }, [recent, stats]);

  const maxDay = Math.max(1, ...last14.map((d) => d.count));

  return (
    <div style={{ fontFamily: "Inter, sans-serif", background: C.bg, minHeight: "100vh" }}>
      <Header activeProgress streak={stats.dayStreak} />

      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "2rem 2rem 3rem" }}>
        {/* Greeting */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            marginBottom: "1.75rem",
            gap: "1rem",
            flexWrap: "wrap",
          }}
        >
          <div>
            <h2
              style={{
                margin: "0 0 5px",
                fontSize: "1.625rem",
                fontWeight: 700,
                color: C.text,
                letterSpacing: "-0.025em",
              }}
            >
              Your progress
            </h2>
            <p
              style={{ margin: 0, fontSize: "0.875rem", color: C.sec, lineHeight: 1.6 }}
            >
              {hasReal
                ? `${DAYS_LEFT} days to the ESAT. You've answered ${totalDone} ${totalDone === 1 ? "question" : "questions"} so far.`
                : "Start a practice session to see your stats, knowledge map, and recent activity here."}
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            <Button variant="ghost" icon="bolt" href="/practice">
              Practise
            </Button>
            {hasReal && (
              <Button
                variant="ghost"
                icon="x"
                onClick={() => setResetOpen(true)}
              >
                Reset
              </Button>
            )}
          </div>
        </div>

        {!hasReal ? (
          <Card padding="3rem 2.5rem" style={{ textAlign: "center" }}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 14,
                background: C.lite,
                border: `1px solid ${C.liteb}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 1.25rem",
              }}
            >
              <Svg icon="activity" size={22} col={C.mid} sw={1.6} />
            </div>
            <h3
              style={{
                margin: "0 0 6px",
                fontSize: "1.1rem",
                fontWeight: 700,
                color: C.text,
                letterSpacing: "-0.01em",
              }}
            >
              No progress data yet
            </h3>
            <p
              style={{
                margin: "0 auto 1.5rem",
                fontSize: "0.875rem",
                color: C.sec,
                lineHeight: 1.6,
                maxWidth: 420,
              }}
            >
              Answer a few ESAT questions and your accuracy, streak, and knowledge map
              will appear here — tracked locally on this device.
            </p>
            <Button variant="primary" icon="play" iconFill="#fff" href="/practice">
              Start practising
            </Button>
          </Card>
        ) : (
          <>
            {/* ── Headline stat cards ── */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: "0.75rem",
                marginBottom: "1.25rem",
              }}
            >
              {cards.map((c) => (
                <StatCard key={c.label} {...c} />
              ))}
            </div>

            {/* ── Knowledge Map + 14-day activity ── */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1.25rem",
                marginBottom: "1.25rem",
              }}
            >
              <Card>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: "1.25rem",
                  }}
                >
                  <div>
                    <h3
                      style={{
                        margin: "0 0 4px",
                        fontSize: "0.9375rem",
                        fontWeight: 600,
                        color: C.text,
                      }}
                    >
                      Knowledge Map
                    </h3>
                    <p style={{ margin: 0, fontSize: "0.8125rem", color: C.ter }}>
                      Accuracy by module · from your practice
                    </p>
                  </div>
                  <Pill bg={C.lite} col={C.mid}>
                    {radarAvg}% avg
                  </Pill>
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: "1.5rem",
                    alignItems: "center",
                  }}
                >
                  <div
                    style={{
                      flex: "0 0 220px",
                      height: 210,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <RadarChartSVG data={radar} />
                  </div>
                  <div
                    style={{
                      flex: 1,
                      display: "flex",
                      flexDirection: "column",
                      gap: 11,
                    }}
                  >
                    {radar.map(({ axis, v, answered, code }) => {
                      const col =
                        v >= 75 ? C.green : v >= 55 ? C.amber : v > 0 ? C.red : C.bdr2;
                      const href = code
                        ? `/practice?module=${encodeURIComponent(code)}`
                        : null;
                      const inner = (
                        <>
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              marginBottom: 5,
                              alignItems: "center",
                            }}
                          >
                            <span
                              style={{
                                fontSize: "0.8125rem",
                                fontWeight: 500,
                                color: C.text,
                              }}
                            >
                              {axis}
                            </span>
                            <span
                              style={{
                                fontFamily: '"JetBrains Mono", monospace',
                                fontSize: "0.75rem",
                                fontWeight: 600,
                                color: col,
                              }}
                            >
                              {answered > 0 ? `${v}%` : "—"}
                              <span
                                style={{
                                  color: C.ter,
                                  fontWeight: 500,
                                  marginLeft: 4,
                                }}
                              >
                                ({answered})
                              </span>
                            </span>
                          </div>
                          <Bar pct={v} color={col} />
                        </>
                      );
                      if (!href) {
                        return <div key={axis}>{inner}</div>;
                      }
                      return (
                        <a
                          key={axis}
                          href={href}
                          title={`Practise ${axis}`}
                          style={{
                            display: "block",
                            textDecoration: "none",
                            color: "inherit",
                          }}
                        >
                          {inner}
                        </a>
                      );
                    })}
                  </div>
                </div>
              </Card>

              {/* 14-day activity */}
              <Card>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: "1.25rem",
                  }}
                >
                  <div>
                    <h3
                      style={{
                        margin: "0 0 4px",
                        fontSize: "0.9375rem",
                        fontWeight: 600,
                        color: C.text,
                      }}
                    >
                      Last 14 days
                    </h3>
                    <p style={{ margin: 0, fontSize: "0.8125rem", color: C.ter }}>
                      Daily question volume
                    </p>
                  </div>
                  <Pill bg={C.alt} col={C.sec}>
                    {last14.reduce((s, d) => s + d.count, 0)} answered
                  </Pill>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-end",
                    gap: 5,
                    height: 150,
                    paddingTop: "0.5rem",
                  }}
                >
                  {last14.map((d, i) => {
                    const h = d.count === 0 ? 4 : Math.max(8, (d.count / maxDay) * 120);
                    const accuracy =
                      d.count === 0 ? 0 : Math.round((d.correct / d.count) * 100);
                    const col =
                      d.count === 0
                        ? C.bdr
                        : accuracy >= 70
                        ? C.green
                        : accuracy >= 50
                        ? C.amber
                        : C.red;
                    const isToday = i === last14.length - 1;
                    return (
                      <div
                        key={d.key}
                        style={{
                          flex: 1,
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          gap: 6,
                          height: "100%",
                          justifyContent: "flex-end",
                        }}
                        title={`${d.key}: ${d.count} answered, ${accuracy}% correct`}
                      >
                        <div
                          style={{
                            width: "100%",
                            maxWidth: 22,
                            height: h,
                            background: col,
                            borderRadius: 4,
                            opacity: d.count === 0 ? 0.5 : 1,
                            outline: isToday ? `2px solid ${C.mid}` : "none",
                            outlineOffset: 1,
                            transition: "height 0.3s ease",
                          }}
                        />
                        <span
                          style={{
                            fontSize: "0.625rem",
                            color: isToday ? C.mid : C.ter,
                            fontFamily: '"JetBrains Mono", monospace',
                            fontWeight: isToday ? 700 : 500,
                          }}
                        >
                          {d.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </Card>
            </div>

            {/* ── Breakdown tables: modules + exams ── */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1.25rem",
                marginBottom: "1.25rem",
              }}
            >
              <BreakdownCard
                title="By module"
                subtitle="Accuracy per subject area"
                rows={stats.byModule.map((m) => ({
                  key: m.code,
                  label: m.label,
                  answered: m.answered,
                  correct: m.correct,
                  accuracy: m.accuracy,
                  href: `/practice?module=${encodeURIComponent(m.code)}`,
                }))}
              />
              <BreakdownCard
                title="By exam"
                subtitle="Accuracy per exam source"
                rows={stats.byExam.map((m) => ({
                  key: m.code,
                  label: prettyExam(m.code),
                  answered: m.answered,
                  correct: m.correct,
                  accuracy: m.accuracy,
                  href: `/practice?exam_type=${encodeURIComponent(m.code)}`,
                }))}
              />
            </div>

            {/* ── Recent activity log ── */}
            <Card padding="1.375rem 1.5rem">
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 7,
                  marginBottom: "1.1rem",
                }}
              >
                <Svg icon="activity" size={15} col={C.mid} sw={1.8} />
                <h3
                  style={{
                    margin: 0,
                    fontSize: "0.9375rem",
                    fontWeight: 600,
                    color: C.text,
                  }}
                >
                  Recent activity
                </h3>
                <span
                  style={{
                    marginLeft: "auto",
                    fontSize: "0.75rem",
                    color: C.ter,
                  }}
                >
                  Last {recent.length} {recent.length === 1 ? "answer" : "answers"}
                </span>
              </div>
              {recent.length === 0 ? (
                <div style={{ fontSize: "0.875rem", color: C.ter, padding: "0.5rem 0" }}>
                  No answers recorded yet.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                  {recent.map((a, i) => {
                    const timeStr =
                      typeof a.timeMs === "number" && a.timeMs > 0
                        ? formatMSS(a.timeMs)
                        : null;
                    return (
                      <div
                        key={`${a.questionId}-${a.ts}-${i}`}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 12,
                          padding: "10px 0",
                          borderTop: i === 0 ? "none" : `1px solid ${C.bdr}`,
                        }}
                      >
                        <div
                          style={{
                            width: 26,
                            height: 26,
                            borderRadius: 7,
                            background: a.correct ? C.gLite : C.rLite,
                            border: `1px solid ${a.correct ? C.gBdr : C.rBdr}`,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            flexShrink: 0,
                          }}
                        >
                          <Svg
                            icon={a.correct ? "check" : "x"}
                            size={13}
                            col={a.correct ? C.green : C.red}
                            sw={2.4}
                          />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div
                            style={{
                              fontSize: "0.8125rem",
                              fontWeight: 500,
                              color: C.text,
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {prettyExam(a.examType)} · {a.module || "General"}
                          </div>
                          {timeStr && (
                            <div
                              style={{
                                fontSize: "0.6875rem",
                                color: C.ter,
                                fontFamily: '"JetBrains Mono", monospace',
                              }}
                            >
                              {timeStr} / question
                            </div>
                          )}
                        </div>
                        <div
                          style={{
                            fontSize: "0.6875rem",
                            color: C.ter,
                            fontFamily: '"JetBrains Mono", monospace',
                            flexShrink: 0,
                          }}
                        >
                          {relativeTime(a.ts)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>
          </>
        )}
      </main>

      {resetOpen && (
        <ResetDialog
          onConfirm={handleReset}
          onCancel={() => setResetOpen(false)}
        />
      )}
    </div>
  );
}

// ── Page header (matches dashboard / practice styling) ──

function Header({ activeProgress, streak }: { activeProgress: boolean; streak: number }) {
  return (
    <header
      style={{
        background: C.surf,
        height: 58,
        borderBottom: `1px solid ${C.bdr}`,
        display: "flex",
        alignItems: "center",
        padding: "0 2rem",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      <Wordmark />
      <nav
        style={{
          display: "flex",
          gap: 4,
          marginLeft: "2.5rem",
          alignItems: "center",
        }}
      >
        <NavPill label="Dashboard" icon="squares" href="/" />
        <NavPill label="Practice" icon="bolt" href="/practice" />
        <NavPill label="Progress" icon="activity" active={activeProgress} href="/progress" />
      </nav>
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
            gap: 7,
            background: C.aLite,
            border: `1px solid ${C.aBdr}`,
            borderRadius: 20,
            padding: "4px 10px 4px 7px",
          }}
        >
          <div
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: C.amber,
            }}
            className="pulse-dot"
          />
          <span style={{ fontSize: "0.75rem", fontWeight: 600, color: C.amber }}>
            {streak}-day streak
          </span>
        </div>
      </div>
    </header>
  );
}

// ── Breakdown card: table of accuracy rows ──

function BreakdownCard({
  title,
  subtitle,
  rows,
}: {
  title: string;
  subtitle: string;
  rows: Array<{
    key: string;
    label: string;
    answered: number;
    correct: number;
    accuracy: number;
    href: string;
  }>;
}) {
  return (
    <Card padding="1.375rem 1.5rem">
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: "1rem",
        }}
      >
        <div>
          <h3
            style={{
              margin: "0 0 4px",
              fontSize: "0.9375rem",
              fontWeight: 600,
              color: C.text,
            }}
          >
            {title}
          </h3>
          <p style={{ margin: 0, fontSize: "0.8125rem", color: C.ter }}>
            {subtitle}
          </p>
        </div>
      </div>
      {rows.length === 0 ? (
        <div style={{ fontSize: "0.875rem", color: C.ter, padding: "0.5rem 0" }}>
          No data yet.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
          {rows.map((r) => {
            const col =
              r.accuracy >= 75
                ? C.green
                : r.accuracy >= 55
                ? C.amber
                : r.accuracy > 0
                ? C.red
                : C.bdr2;
            return (
              <a
                key={r.key || r.label}
                href={r.href}
                style={{
                  display: "block",
                  textDecoration: "none",
                  color: "inherit",
                }}
                title={`Practise ${r.label}`}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 5,
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.8125rem",
                      fontWeight: 500,
                      color: C.text,
                    }}
                  >
                    {r.label}
                  </span>
                  <span
                    style={{
                      fontFamily: '"JetBrains Mono", monospace',
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: col,
                    }}
                  >
                    {r.answered > 0 ? `${r.accuracy}%` : "—"}
                    <span
                      style={{
                        color: C.ter,
                        fontWeight: 500,
                        marginLeft: 4,
                      }}
                    >
                      ({r.correct}/{r.answered})
                    </span>
                  </span>
                </div>
                <Bar pct={r.accuracy} color={col} />
              </a>
            );
          })}
        </div>
      )}
    </Card>
  );
}

// ── Reset confirmation dialog ──

function ResetDialog({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onCancel}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: C.surf,
          border: `1px solid ${C.bdr}`,
          borderRadius: 14,
          padding: "1.5rem 1.75rem",
          maxWidth: 400,
          boxShadow: SH.lifted,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 10,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 9,
              background: C.rLite,
              border: `1px solid ${C.rBdr}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <Svg icon="warn" size={16} col={C.red} sw={1.8} />
          </div>
          <h3
            style={{
              margin: 0,
              fontSize: "1rem",
              fontWeight: 700,
              color: C.text,
              letterSpacing: "-0.01em",
            }}
          >
            Reset all progress?
          </h3>
        </div>
        <p
          style={{
            margin: "0 0 1.25rem",
            fontSize: "0.875rem",
            color: C.sec,
            lineHeight: 1.6,
          }}
        >
          This permanently clears your answer history, streak, and per-module stats on
          this device. There is no undo.
        </p>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            variant="primary"
            icon="x"
            onClick={onConfirm}
            style={{ background: C.red }}
          >
            Reset everything
          </Button>
        </div>
      </div>
    </div>
  );
}
