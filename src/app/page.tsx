"use client";

import { useEffect, useState } from "react";
import {
  C,
  SH,
  DAYS_LEFT,
  TOPICS,
  RADAR_DATA,
} from "@/lib/constants";
import {
  loadProgress,
  computeStats,
  buildRadarData,
  formatMSS,
  type ProgressStats,
} from "@/lib/progress";
import { Svg } from "@/components/icons";
import { Bar, Pill, Wordmark, Label, NavPill } from "@/components/atoms";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { StatCard } from "@/components/StatCard";
import { RadarChartSVG } from "@/components/RadarChartSVG";

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

/**
 * Build the four stat cards from real progress when available, falling back
 * to the design-time mock values for first-time users so the dashboard
 * never looks empty.
 */
function buildStats(stats: ProgressStats | null): StatCardProps[] {
  if (!stats || !stats.hasData) {
    return [
      {
        icon: "flame",
        label: "Day Streak",
        val: "0",
        unit: "days",
        col: C.amber,
        bg: "#FFF7ED",
        delta: "new",
        deltaCol: C.mid,
      },
      {
        icon: "clock",
        label: "Avg Time / Q",
        val: "—",
        unit: "min",
        col: C.mid,
        bg: C.lite,
        delta: "—",
        deltaCol: C.ter,
      },
      {
        icon: "trendUp",
        label: "Accuracy",
        val: "—",
        unit: "%",
        col: C.green,
        bg: C.gLite,
        delta: "—",
        deltaCol: C.ter,
      },
      {
        icon: "sparkle",
        label: "Questions Done",
        val: "0",
        unit: "total",
        col: C.purp,
        bg: C.pLite,
        delta: "new",
        deltaCol: C.mid,
      },
    ];
  }
  const accuracyDelta =
    stats.accuracy >= 70 ? "strong" : stats.accuracy >= 50 ? "ok" : "keep going";
  const accuracyDeltaCol = stats.accuracy >= 70 ? C.green : stats.accuracy >= 50 ? C.amber : C.red;
  return [
    {
      icon: "flame",
      label: "Day Streak",
      val: String(stats.dayStreak),
      unit: stats.dayStreak === 1 ? "day" : "days",
      col: C.amber,
      bg: "#FFF7ED",
      delta: stats.activeDayCount === 1 ? "1 day" : `${stats.activeDayCount} days`,
      deltaCol: C.mid,
    },
    {
      icon: "clock",
      label: "Avg Time / Q",
      val: formatMSS(stats.avgTimeMs),
      unit: "min",
      col: C.mid,
      bg: C.lite,
      delta: stats.totalAnswered === 0 ? "—" : `${stats.totalAnswered} ans`,
      deltaCol: C.ter,
    },
    {
      icon: "trendUp",
      label: "Accuracy",
      val: String(stats.accuracy),
      unit: "%",
      col: stats.accuracy >= 70 ? C.green : stats.accuracy >= 50 ? C.amber : C.red,
      bg: stats.accuracy >= 70 ? C.gLite : stats.accuracy >= 50 ? C.aLite : C.rLite,
      delta: accuracyDelta,
      deltaCol: accuracyDeltaCol,
    },
    {
      icon: "sparkle",
      label: "Questions Done",
      val: String(stats.totalAnswered),
      unit: "total",
      col: C.purp,
      bg: C.pLite,
      delta: `${stats.totalCorrect} ✓`,
      deltaCol: C.green,
    },
  ];
}

export default function Dashboard() {
  const [stats, setStats] = useState<ProgressStats | null>(null);

  // localStorage only exists in the browser — load on mount so SSR renders
  // the empty state and the client hydrates real numbers afterwards.
  useEffect(() => {
    const s = computeStats(loadProgress());
    setStats(s);
    // Re-sync when the user returns from a practice session in another tab.
    const onStorage = (e: StorageEvent) => {
      if (e.key === "esat-progress-v1") {
        setStats(computeStats(loadProgress()));
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const hasReal = !!(stats && stats.hasData);
  // Normalise the mock fallback so it carries `code` too — lets every radar
  // row render identically regardless of whether real data exists.
  const radar = hasReal
    ? buildRadarData(stats!)
    : RADAR_DATA.map((d) => ({ ...d, answered: 0, code: "" }));
  const radarAvg = radar.length
    ? Math.round(radar.reduce((s, d) => s + d.v, 0) / radar.length)
    : 0;

  // "Needs Attention" — weakest modules from real data, falling back to the
  // design-time TOPICS mock for first-time users. Carries the module code so
  // each row can deep-link into topic-filtered practice.
  type WeakItem = { name: string; str: number; s: string; code?: string };
  let weak: WeakItem[];
  if (hasReal) {
    weak = stats!.byModule
      .filter((m) => m.answered > 0)
      .slice()
      .sort((a, b) => a.accuracy - b.accuracy)
      .slice(0, 5)
      .map((m) => ({
        name: m.label,
        str: m.accuracy,
        s: `${m.correct}/${m.answered} correct`,
        code: m.code,
      }));
    if (weak.length === 0) weak = [];
  } else {
    weak = Object.entries(TOPICS)
      .flatMap(([s, ts]) => ts.map((t) => ({ ...t, s })))
      .sort((a, b) => a.str - b.str)
      .slice(0, 5);
  }

  const statsCards = buildStats(stats);
  const dayStreakPill = hasReal ? stats!.dayStreak : 0;
  const totalDone = hasReal ? stats!.totalAnswered : 0;

  return (
    <div style={{ fontFamily: "Inter, sans-serif", background: C.bg, minHeight: "100vh" }}>
      {/* ── Navigation bar ── */}
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
          <NavPill label="Dashboard" icon="squares" active href="/" />
          <NavPill label="Practice" icon="bolt" href="/practice" />
          <NavPill label="Mock Exam" icon="pencil" href="/mock-exam" />
          <NavPill label="Progress" icon="activity" href="/progress" />
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
              {dayStreakPill}-day streak
            </span>
          </div>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              background: C.lite,
              border: `2px solid ${C.liteb}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
            }}
          >
            <Svg icon="user" size={14} col={C.mid} />
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "2rem 2rem 3rem" }}>
        {/* Greeting */}
        <div style={{ marginBottom: "1.75rem" }}>
          <h2
            style={{
              margin: "0 0 5px",
              fontSize: "1.625rem",
              fontWeight: 700,
              color: C.text,
              letterSpacing: "-0.025em",
            }}
          >
            Good morning, Alex.
          </h2>
          <p style={{ margin: 0, fontSize: "0.875rem", color: C.sec, lineHeight: 1.6 }}>
            {DAYS_LEFT} days to the ESAT. Your weakest area right now is{" "}
            <span style={{ fontWeight: 600, color: C.text }}>Proof &amp; Logic</span>{" "}
            &mdash; today&apos;s session targets it.
          </p>
        </div>

        {/* ── Countdown banner ── */}
        <div
          style={{
            background: C.blue,
            borderRadius: 14,
            padding: "1.375rem 1.875rem",
            marginBottom: "1.25rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            position: "relative",
            overflow: "hidden",
            boxShadow:
              "0 4px 24px rgba(26,71,184,0.18), 0 1px 4px rgba(26,71,184,0.12)",
          }}
        >
          {/* Decorative arcs */}
          <svg
            style={{
              position: "absolute",
              right: -60,
              top: "50%",
              transform: "translateY(-50%)",
              opacity: 0.055,
              pointerEvents: "none",
            }}
            width="320"
            height="320"
            viewBox="0 0 320 320"
            aria-hidden="true"
          >
            <circle cx="160" cy="160" r="145" fill="none" stroke="white" strokeWidth="56" />
          </svg>
          <svg
            style={{
              position: "absolute",
              right: 40,
              top: "50%",
              transform: "translateY(-50%)",
              opacity: 0.04,
              pointerEvents: "none",
            }}
            width="160"
            height="160"
            viewBox="0 0 160 160"
            aria-hidden="true"
          >
            <circle cx="80" cy="80" r="68" fill="none" stroke="white" strokeWidth="30" />
          </svg>

          <div style={{ position: "relative" }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                background: "rgba(255,255,255,0.12)",
                borderRadius: 20,
                padding: "3px 10px",
                marginBottom: 10,
              }}
            >
              <div
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: "50%",
                  background: "rgba(255,255,255,0.6)",
                }}
              />
              <span
                style={{
                  fontSize: "0.6875rem",
                  fontWeight: 600,
                  color: "rgba(255,255,255,0.7)",
                  letterSpacing: "0.07em",
                  textTransform: "uppercase",
                }}
              >
                ESAT 2026
              </span>
            </div>
            <div
              style={{
                fontSize: "1.125rem",
                fontWeight: 700,
                color: "#fff",
                letterSpacing: "-0.02em",
                marginBottom: 5,
              }}
            >
              Thursday, 9 October
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {["Cambridge", "Imperial College", "UCL"].map((u, i) => (
                <span key={u} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {i > 0 && (
                    <span style={{ color: "rgba(255,255,255,0.25)", fontSize: "0.75rem" }}>
                      &middot;
                    </span>
                  )}
                  <span style={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" }}>
                    {u}
                  </span>
                </span>
              ))}
            </div>
          </div>

          <div style={{ textAlign: "right", position: "relative" }}>
            <div
              style={{
                fontFamily: '"JetBrains Mono", monospace',
                fontSize: "3.75rem",
                fontWeight: 700,
                color: "#fff",
                lineHeight: 1,
                letterSpacing: "-0.05em",
              }}
            >
              {DAYS_LEFT}
            </div>
            <div
              style={{
                fontSize: "0.6875rem",
                fontWeight: 600,
                color: "rgba(255,255,255,0.45)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginTop: 5,
              }}
            >
              days remaining
            </div>
          </div>
        </div>

        {/* ── Main grid: Knowledge Map + Stat Cards ── */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 256px",
            gap: "1.25rem",
            marginBottom: "1.25rem",
          }}
        >
          {/* Knowledge Map */}
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
                  {hasReal
                    ? "Accuracy by module \u00B7 from your practice"
                    : "Accuracy by module \u00B7 sample data"}
                </p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-end",
                    background: C.lite,
                    border: `1px solid ${C.liteb}`,
                    borderRadius: 8,
                    padding: "5px 10px",
                  }}
                >
                  <span
                    style={{
                      fontFamily: '"JetBrains Mono", monospace',
                      fontSize: "1.125rem",
                      fontWeight: 700,
                      color: C.mid,
                      lineHeight: 1,
                    }}
                  >
                    {radarAvg}%
                  </span>
                  <span
                    style={{
                      fontSize: "0.625rem",
                      color: C.ter,
                      fontWeight: 600,
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                      marginTop: 2,
                    }}
                  >
                    avg
                  </span>
                </div>
                <Pill bg={C.alt} col={C.sec}>
                  {totalDone} {totalDone === 1 ? "question" : "questions"}
                </Pill>
              </div>
            </div>
            <div style={{ display: "flex", gap: "2rem", alignItems: "center" }}>
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
                  gap: 12,
                }}
              >
                {radar.map(({ axis, v, code }) => {
                  const col = v >= 75 ? C.green : v >= 55 ? C.amber : v > 0 ? C.red : C.bdr2;
                  // When real data exists we have a module code, so wrap the
                  // row in a link to filtered practice.
                  const href = hasReal && code ? `/practice?module=${encodeURIComponent(code)}` : null;
                  const rowInner = (
                    <>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: 6,
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
                          {v > 0 ? `${v}%` : "—"}
                        </span>
                      </div>
                      <Bar pct={v} color={col} />
                    </>
                  );
                  if (!href) {
                    return <div key={axis}>{rowInner}</div>;
                  }
                  return (
                    <a
                      key={axis}
                      href={href}
                      title={`Practise ${axis}`}
                      style={{ display: "block", textDecoration: "none", color: "inherit" }}
                    >
                      {rowInner}
                    </a>
                  );
                })}
              </div>
            </div>
          </Card>

          {/* Stat cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {statsCards.map((stat) => (
              <StatCard key={stat.label} {...stat} />
            ))}
          </div>
        </div>

        {/* ── Bottom row: Needs Attention + CTA ── */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "300px 1fr",
            gap: "1.25rem",
          }}
        >
          {/* Needs Attention */}
          <Card padding="1.375rem 1.5rem">
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 7,
                marginBottom: "1.1rem",
              }}
            >
              <Svg icon="warn" size={15} col={C.amber} sw={1.8} />
              <h3
                style={{
                  margin: 0,
                  fontSize: "0.9375rem",
                  fontWeight: 600,
                  color: C.text,
                }}
              >
                Needs Attention
              </h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {weak.length === 0 && (
                <div
                  style={{
                    fontSize: "0.8125rem",
                    color: C.ter,
                    lineHeight: 1.6,
                    padding: "0.5rem 0",
                  }}
                >
                  Answer a few questions to see your weakest topics here.
                </div>
              )}
              {weak.map(({ name, str, s, code }) => {
                const col = str < 50 ? C.red : C.amber;
                const href = code ? `/practice?module=${encodeURIComponent(code)}` : null;
                const inner = (
                  <>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-end",
                        marginBottom: 5,
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontSize: "0.8125rem",
                            fontWeight: 500,
                            color: C.text,
                            lineHeight: 1.3,
                          }}
                        >
                          {name}
                        </div>
                        <div style={{ fontSize: "0.6875rem", color: C.ter, marginTop: 2 }}>
                          {s}
                        </div>
                      </div>
                      <span
                        style={{
                          fontFamily: '"JetBrains Mono", monospace',
                          fontSize: "0.8125rem",
                          fontWeight: 700,
                          color: col,
                          flexShrink: 0,
                          marginLeft: 8,
                        }}
                      >
                        {str}%
                      </span>
                    </div>
                    <Bar pct={str} color={col} />
                  </>
                );
                if (!href) {
                  return <div key={name}>{inner}</div>;
                }
                return (
                  <a
                    key={name}
                    href={href}
                    title={`Practise ${name}`}
                    style={{ display: "block", textDecoration: "none", color: "inherit" }}
                  >
                    {inner}
                  </a>
                );
              })}
            </div>
          </Card>

          {/* CTA */}
          <Card padding="1.625rem 1.75rem" style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ flex: 1 }}>
              <h3
                style={{
                  margin: "0 0 8px",
                  fontSize: "1.1rem",
                  fontWeight: 700,
                  color: C.text,
                  letterSpacing: "-0.02em",
                }}
              >
                Ready to practise?
              </h3>
              <p
                style={{
                  margin: "0 0 16px",
                  fontSize: "0.875rem",
                  color: C.sec,
                  lineHeight: 1.7,
                  maxWidth: 480,
                }}
              >
                Ten AI-generated questions, tuned to your weakest topics, at real ESAT
                difficulty and pace &mdash; with instant feedback and full worked
                solutions.
              </p>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {[
                  { icon: "sparkle" as const, label: "AI-generated" },
                  { icon: "clock" as const, label: "~15 minutes" },
                  { icon: "book" as const, label: "Worked solutions" },
                  { icon: "bolt" as const, label: "Keyboard-first" },
                ].map(({ icon, label }) => (
                  <span
                    key={label}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 5,
                      fontSize: "0.75rem",
                      color: C.mid,
                      fontWeight: 500,
                      background: C.lite,
                      padding: "4px 10px",
                      borderRadius: 20,
                      border: `1px solid ${C.liteb}`,
                    }}
                  >
                    <Svg icon={icon} size={11} col={C.mid} sw={2} />
                    {label}
                  </span>
                ))}
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: "1.5rem" }}>
              <Button
                variant="primary"
                icon="play"
                iconFill="#fff"
                href="/practice"
                style={{ flex: 1 }}
              >
                Start Practising
              </Button>
              <Button
                variant="ghost"
                icon="pencil"
                href="/mock-exam"
                title="Mock Exam — timed full-length practice exam"
              >
                Mock Exam
              </Button>
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}
