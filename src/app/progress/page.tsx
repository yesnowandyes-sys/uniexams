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
    return (
      <div className={styles.page}>
        <Header activeProgress={false} streak={0} />
        <main className={styles.main}>
          <div style={{ color: C.sec, fontSize: "0.875rem" }}>Loading…</div>
        </main>
      </div>
    );
  }

  const cards = buildStatsCards(stats);
  const totalDone = stats.totalAnswered;

  const last14 = useMemo(() => {
    const days: { key: string; label: string; count: number; correct: number }[] = [];
    const cursor = new Date();
    for (let i = 13; i >= 0; i--) {
      const d = new Date(cursor);
      d.setDate(d.getDate() - i);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
      days.push({ key, label: d.toLocaleDateString(undefined, { weekday: "narrow" }), count: 0, correct: 0 });
    }
    const byKey = new Map(days.map((d) => [d.key, d]));
    const all = loadProgress().attempts;
    for (const a of all) {
      const d = new Date(a.ts);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
      const bucket = byKey.get(key);
      if (!bucket) continue;
      bucket.count++;
      if (a.correct) bucket.correct++;
    }
    return days;
  }, [recent, stats]);

  const maxDay = Math.max(1, ...last14.map((d) => d.count));

  return (
    <div className={styles.page}>
      <Header activeProgress streak={stats.dayStreak} />

      <main className={styles.main}>
        {/* Greeting */}
        <div className={styles.topRow}>
          <div>
            <h2 className={styles.topTitle}>Your progress</h2>
            <p className={styles.topSub}>
              {hasReal
                ? `${DAYS_LEFT} days to the ESAT. You've answered ${totalDone} ${totalDone === 1 ? "question" : "questions"} so far.`
                : "Start a practice session to see your stats, knowledge map, and recent activity here."}
            </p>
          </div>
          <div className={styles.topActions}>
            <Button variant="ghost" icon="bolt" href="/practice">Practise</Button>
            {hasReal && (
              <Button variant="ghost" icon="x" onClick={() => setResetOpen(true)}>Reset</Button>
            )}
          </div>
        </div>

        {!hasReal ? (
          <Card padding="3rem 2.5rem" style={{ textAlign: "center" }}>
            <div className={styles.emptyIcon}>
              <Svg icon="activity" size={22} col={C.mid} sw={1.6} />
            </div>
            <h3 className={styles.emptyTitle}>No progress data yet</h3>
            <p className={styles.emptyDesc}>
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
            <div className={styles.statGrid}>
              {cards.map((c) => (
                <StatCard key={c.label} {...c} />
              ))}
            </div>

            {/* ── Knowledge Map + 14-day activity ── */}
            <div className={styles.twoColGrid}>
              <Card>
                <div className={styles.knowledgeMapHeader}>
                  <div>
                    <h3 className={styles.sectionTitle}>Knowledge Map</h3>
                    <p className={styles.sectionSub}>
                      Accuracy by module · from your practice
                    </p>
                  </div>
                  <Pill bg={C.lite} col={C.mid}>{radarAvg}% avg</Pill>
                </div>
                <div className={styles.knowledgeMapContent}>
                  <div className={styles.radarContainer}>
                    <RadarChartSVG data={radar} />
                  </div>
                  <div className={styles.radarBars}>
                    {radar.map(({ axis, v, answered, code }) => {
                      const col = v >= 75 ? C.green : v >= 55 ? C.amber : v > 0 ? C.red : C.bdr2;
                      const href = code ? `/practice?module=${encodeURIComponent(code)}` : null;
                      const inner = (
                        <>
                          <div className={styles.radarRowHeader}>
                            <span className={styles.radarRowName}>{axis}</span>
                            <span className={styles.radarRowPct} style={{ color: col }}>
                              {answered > 0 ? `${v}%` : "—"}
                              <span style={{ color: C.ter, fontWeight: 500, marginLeft: 4 }}>({answered})</span>
                            </span>
                          </div>
                          <Bar pct={v} color={col} />
                        </>
                      );
                      if (!href) return <div key={axis}>{inner}</div>;
                      return (
                        <a key={axis} href={href} title={`Practise ${axis}`} className={styles.radarRowLink}>
                          {inner}
                        </a>
                      );
                    })}
                  </div>
                </div>
              </Card>

              {/* 14-day activity */}
              <Card>
                <div className={styles.knowledgeMapHeader}>
                  <div>
                    <h3 className={styles.sectionTitle}>Last 14 days</h3>
                    <p className={styles.sectionSub}>
                      Daily question volume
                    </p>
                  </div>
                  <Pill bg={C.alt} col={C.sec}>
                    {last14.reduce((s, d) => s + d.count, 0)} answered
                  </Pill>
                </div>
                <div className={styles.activityChart}>
                  {last14.map((d, i) => {
                    const h = d.count === 0 ? 4 : Math.max(8, (d.count / maxDay) * 120);
                    const accuracy = d.count === 0 ? 0 : Math.round((d.correct / d.count) * 100);
                    const col = d.count === 0 ? C.bdr : accuracy >= 70 ? C.green : accuracy >= 50 ? C.amber : C.red;
                    const isToday = i === last14.length - 1;
                    return (
                      <div key={d.key} className={styles.activityCol} title={`${d.key}: ${d.count} answered, ${accuracy}% correct`}>
                        <div
                          className={styles.activityBar}
                          style={{
                            height: h,
                            background: col,
                            opacity: d.count === 0 ? 0.5 : 1,
                            outline: isToday ? `2px solid ${C.mid}` : "none",
                            outlineOffset: 1,
                          }}
                        />
                        <span className={styles.activityLabel} style={{ color: isToday ? C.mid : C.ter, fontWeight: isToday ? 700 : 500 }}>
                          {d.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </Card>
            </div>

            {/* ── Breakdown tables ── */}
            <div className={styles.twoColGrid}>
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
              <div className={styles.recentHeader}>
                <Svg icon="activity" size={15} col={C.mid} sw={1.8} />
                <h3 className={styles.sectionTitle}>Recent activity</h3>
                <span className={styles.recentCount}>
                  Last {recent.length} {recent.length === 1 ? "answer" : "answers"}
                </span>
              </div>
              {recent.length === 0 ? (
                <div className={styles.emptyText}>No answers recorded yet.</div>
              ) : (
                <div className={styles.recentList}>
                  {recent.map((a, i) => {
                    const timeStr = typeof a.timeMs === "number" && a.timeMs > 0 ? formatMSS(a.timeMs) : null;
                    return (
                      <div
                        key={`${a.questionId}-${a.ts}-${i}`}
                        className={styles.recentItem}
                        style={{ borderTop: i === 0 ? "none" : `1px solid ${C.bdr}` }}
                      >
                        <div
                          className={styles.recentIcon}
                          style={{
                            background: a.correct ? C.gLite : C.rLite,
                            border: `1px solid ${a.correct ? C.gBdr : C.rBdr}`,
                          }}
                        >
                          <Svg icon={a.correct ? "check" : "x"} size={13} col={a.correct ? C.green : C.red} sw={2.4} />
                        </div>
                        <div className={styles.recentItemBody}>
                          <div className={styles.recentItemText}>
                            {prettyExam(a.examType)} · {a.module || "General"}
                          </div>
                          {timeStr && (
                            <div className={styles.recentItemTimeMeta}>
                              {timeStr} / question
                            </div>
                          )}
                        </div>
                        <div className={styles.recentItemRelTime}>
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
        <ResetDialog onConfirm={handleReset} onCancel={() => setResetOpen(false)} />
      )}
    </div>
  );
}

// ── Page header ──

function Header({ activeProgress, streak }: { activeProgress: boolean; streak: number }) {
  return (
    <header className={styles.header}>
      <Wordmark />
      <nav className={styles.nav}>
        <NavPill label="Dashboard" icon="squares" href="/" />
        <NavPill label="Practice" icon="bolt" href="/practice" />
        <NavPill label="Progress" icon="activity" active={activeProgress} href="/progress" />
      </nav>
      <div className={styles.headerRight}>
        <div className={styles.streakPill}>
          <div className={`${styles.streakDot} pulse-dot`} />
          <span className={styles.streakPillText}>{streak}-day streak</span>
        </div>
      </div>
    </header>
  );
}

// ── Breakdown card ──

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
      <div className={styles.knowledgeMapHeader}>
        <div>
          <h3 className={styles.sectionTitle}>{title}</h3>
          <p className={styles.sectionSub}>{subtitle}</p>
        </div>
      </div>
      {rows.length === 0 ? (
        <div className={styles.emptyText}>No data yet.</div>
      ) : (
        <div className={styles.breakdownList}>
          {rows.map((r) => {
            const col = r.accuracy >= 75 ? C.green : r.accuracy >= 55 ? C.amber : r.accuracy > 0 ? C.red : C.bdr2;
            return (
              <a key={r.key || r.label} href={r.href} className={styles.radarRowLink} title={`Practise ${r.label}`}>
                <div className={styles.radarRowHeader}>
                  <span className={styles.radarRowName}>{r.label}</span>
                  <span className={styles.radarRowPct} style={{ color: col }}>
                    {r.answered > 0 ? `${r.accuracy}%` : "—"}
                    <span style={{ color: C.ter, fontWeight: 500, marginLeft: 4 }}>({r.correct}/{r.answered})</span>
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

function ResetDialog({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className={styles.dialogOverlay} role="dialog" aria-modal="true" onClick={onCancel}>
      <div className={styles.dialogBox} onClick={(e) => e.stopPropagation()}>
        <div className={styles.dialogHeader}>
          <div className={styles.dialogIcon}>
            <Svg icon="warn" size={16} col={C.red} sw={1.8} />
          </div>
          <h3 className={styles.dialogTitle}>Reset all progress?</h3>
        </div>
        <p className={styles.dialogDesc}>
          This permanently clears your answer history, streak, and per-module stats on
          this device. There is no undo.
        </p>
        <div className={styles.dialogActions}>
          <Button variant="ghost" onClick={onCancel}>Cancel</Button>
          <Button variant="primary" icon="x" onClick={onConfirm} style={{ background: C.red }}>
            Reset everything
          </Button>
        </div>
      </div>
    </div>
  );
}
