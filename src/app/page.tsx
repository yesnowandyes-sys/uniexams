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
import styles from "./page.module.css";

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
    <div className={styles.page}>
      {/* ── Navigation bar ── */}
      <header className={styles.header}>
        <Wordmark />
        <nav className={styles.nav}>
          <NavPill label="Dashboard" icon="squares" active href="/" />
          <NavPill label="Practice" icon="bolt" href="/practice" />
          <NavPill label="Mock Exam" icon="pencil" href="/mock-exam" />
          <NavPill label="Progress" icon="activity" href="/progress" />
        </nav>
        <div className={styles.headerRight}>
          <div className={styles.streakPill}>
            <div className={`${styles.streakDot} pulse-dot`} />
            <span className={styles.streakPillText}>
              {dayStreakPill}-day streak
            </span>
          </div>
          <div className={styles.userAvatar}>
            <Svg icon="user" size={14} col={C.mid} />
          </div>
        </div>
      </header>

      <main className={styles.main}>
        {/* Greeting */}
        <div className={styles.greeting}>
          <h2 className={styles.greetingTitle}>
            Good morning, Alex.
          </h2>
          <p className={styles.greetingSub}>
            {DAYS_LEFT} days to the ESAT. Your weakest area right now is{" "}
            <span style={{ fontWeight: 600, color: C.text }}>Proof &amp; Logic</span>{" "}
            &mdash; today&apos;s session targets it.
          </p>
        </div>

        {/* ── Countdown banner ── */}
        <div className={styles.countdownBanner}>
          {/* Decorative arcs */}
          <svg
            className={`${styles.countdownDecor} ${styles.countdownDecorLarge}`}
            width="320"
            height="320"
            viewBox="0 0 320 320"
            aria-hidden="true"
          >
            <circle cx="160" cy="160" r="145" fill="none" stroke="white" strokeWidth="56" />
          </svg>
          <svg
            className={`${styles.countdownDecor} ${styles.countdownDecorSmall}`}
            width="160"
            height="160"
            viewBox="0 0 160 160"
            aria-hidden="true"
          >
            <circle cx="80" cy="80" r="68" fill="none" stroke="white" strokeWidth="30" />
          </svg>

          <div className={styles.countdownLeft}>
            <div className={styles.countdownBadge}>
              <div className={styles.countdownBadgeDot} />
              <span className={styles.countdownBadgeText}>
                ESAT 2026
              </span>
            </div>
            <div className={styles.countdownDate}>
              Thursday, 9 October
            </div>
            <div className={styles.countdownUnis}>
              {["Cambridge", "Imperial College", "UCL"].map((u, i) => (
                <span key={u} className={styles.countdownUni}>
                  {i > 0 && (
                    <span className={styles.countdownDot}>
                      &middot;
                    </span>
                  )}
                  {u}
                </span>
              ))}
            </div>
          </div>

          <div className={styles.countdownRight}>
            <div className={styles.countdownNumber}>
              {DAYS_LEFT}
            </div>
            <div className={styles.countdownLabel}>
              days remaining
            </div>
          </div>
        </div>

        {/* ── Main grid: Knowledge Map + Stat Cards ── */}
        <div className={styles.mainGrid}>
          {/* Knowledge Map */}
          <Card>
            <div className={styles.knowledgeMapHeader}>
              <div>
                <h3 className={styles.sectionTitle}>
                  Knowledge Map
                </h3>
                <p className={styles.sectionSub}>
                  {hasReal
                    ? "Accuracy by module \u00B7 from your practice"
                    : "Accuracy by module \u00B7 sample data"}
                </p>
              </div>
              <div className={styles.knowledgeMapActions}>
                <div className={styles.knowledgeMapAvg}>
                  <span className={styles.knowledgeMapAvgNum}>
                    {radarAvg}%
                  </span>
                  <span className={styles.knowledgeMapAvgLabel}>
                    avg
                  </span>
                </div>
                <Pill bg={C.alt} col={C.sec}>
                  {totalDone} {totalDone === 1 ? "question" : "questions"}
                </Pill>
              </div>
            </div>
            <div className={styles.knowledgeMapContent}>
              <div className={styles.radarContainer}>
                <RadarChartSVG data={radar} />
              </div>
              <div className={styles.radarBars}>
                {radar.map(({ axis, v, code }) => {
                  const col = v >= 75 ? C.green : v >= 55 ? C.amber : v > 0 ? C.red : C.bdr2;
                  const href = hasReal && code ? `/practice?module=${encodeURIComponent(code)}` : null;
                  const rowInner = (
                    <>
                      <div className={styles.radarRowHeader}>
                        <span className={styles.radarRowName}>
                          {axis}
                        </span>
                        <span className={styles.radarRowPct} style={{ color: col }}>
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
                      className={styles.radarRowLink}
                    >
                      {rowInner}
                    </a>
                  );
                })}
              </div>
            </div>
          </Card>

          {/* Stat cards */}
          <div className={styles.statCardsCol}>
            {statsCards.map((stat) => (
              <StatCard key={stat.label} {...stat} />
            ))}
          </div>
        </div>

        {/* ── Bottom row: Needs Attention + CTA ── */}
        <div className={styles.bottomGrid}>
          {/* Needs Attention */}
          <Card padding="1.375rem 1.5rem">
            <div className={styles.needsAttentionHeader}>
              <Svg icon="warn" size={15} col={C.amber} sw={1.8} />
              <h3 className={styles.sectionTitle}>
                Needs Attention
              </h3>
            </div>
            <div className={styles.weakList}>
              {weak.length === 0 && (
                <div className={styles.emptyState}>
                  Answer a few questions to see your weakest topics here.
                </div>
              )}
              {weak.map(({ name, str, s, code }) => {
                const col = str < 50 ? C.red : C.amber;
                const href = code ? `/practice?module=${encodeURIComponent(code)}` : null;
                const inner = (
                  <>
                    <div className={styles.weakRowHeader}>
                      <div>
                        <div className={styles.weakRowName}>
                          {name}
                        </div>
                        <div className={styles.weakRowSub}>
                          {s}
                        </div>
                      </div>
                      <span className={styles.weakRowPct} style={{ color: col }}>
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
                    className={styles.weakRowLink}
                  >
                    {inner}
                  </a>
                );
              })}
            </div>
          </Card>

          {/* CTA */}
          <Card padding="1.625rem 1.75rem" className={styles.ctaCard}>
            <div className={styles.ctaContent}>
              <h3 className={styles.ctaTitle}>
                Ready to practise?
              </h3>
              <p className={styles.ctaDesc}>
                Ten AI-generated questions, tuned to your weakest topics, at real ESAT
                difficulty and pace &mdash; with instant feedback and full worked
                solutions.
              </p>
              <div className={styles.ctaBadges}>
                {[
                  { icon: "sparkle" as const, label: "AI-generated" },
                  { icon: "clock" as const, label: "~15 minutes" },
                  { icon: "book" as const, label: "Worked solutions" },
                  { icon: "bolt" as const, label: "Keyboard-first" },
                ].map(({ icon, label }) => (
                  <span key={label} className={styles.ctaBadge}>
                    <Svg icon={icon} size={11} col={C.mid} sw={2} />
                    {label}
                  </span>
                ))}
              </div>
            </div>
            <div className={styles.ctaButtons}>
              <Button
                variant="primary"
                icon="play"
                iconFill="#fff"
                href="/practice"
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
