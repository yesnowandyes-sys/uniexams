/**
 * Client-side progress tracking (ESA-14).
 *
 * Records every scored answer to localStorage and derives the stats the
 * dashboard renders: total attempted, accuracy, current streak, average
 * time per question, and per-module / per-exam breakdowns for the Knowledge
 * Map (RadarChartSVG) and "Needs Attention" panels.
 *
 * The store is intentionally simple — a single append-only array under one
 * localStorage key. We cap the log at MAX_ATTEMPTS so it cannot grow
 * unbounded across years of use; oldest entries are dropped first.
 */

export interface AttemptRecord {
  /** Question id, so we could later join back to the corpus. */
  questionId: string;
  /** Denormalised from the question so stats work without a DB round-trip. */
  examType: string;
  module: string;
  correct: boolean;
  timeMs?: number;
  /** Epoch milliseconds when the answer was committed. */
  ts: number;
}

export interface ProgressState {
  attempts: AttemptRecord[];
}

const KEY = "esat-progress-v1";
/** Cap so the log is bounded; ~5000 sessions * 10 = plenty of headroom. */
const MAX_ATTEMPTS = 5000;

/** Friendly display labels for the module codes stored on questions. */
export const MODULE_LABELS: Record<string, string> = {
  maths1: "Maths 1",
  maths2: "Maths 2",
  physics: "Physics",
  chemistry: "Chemistry",
  biology: "Biology",
};

/** Canonical radar axis order — matches the original design mock. */
export const RADAR_AXIS_ORDER = [
  "maths1",
  "physics",
  "chemistry",
  "biology",
  "maths2",
];

export function moduleLabel(code: string): string {
  return MODULE_LABELS[code] ?? (code ? code : "General");
}

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

export function loadProgress(): ProgressState {
  if (!isBrowser()) return { attempts: [] };
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { attempts: [] };
    const parsed = JSON.parse(raw) as Partial<ProgressState>;
    if (!parsed || !Array.isArray(parsed.attempts)) return { attempts: [] };
    return { attempts: parsed.attempts.filter(isValidAttempt) };
  } catch {
    return { attempts: [] };
  }
}

export function saveProgress(state: ProgressState): void {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* Quota or serialization error — progress is best-effort, never fatal. */
  }
}

function isValidAttempt(a: unknown): a is AttemptRecord {
  if (!a || typeof a !== "object") return false;
  const r = a as Record<string, unknown>;
  return (
    typeof r.questionId === "string" &&
    typeof r.examType === "string" &&
    typeof r.module === "string" &&
    typeof r.correct === "boolean" &&
    typeof r.ts === "number"
  );
}

/**
 * Append an attempt. Returns the new state so callers can use it without a
 * follow-up load (the underlying localStorage is also updated).
 */
export function recordAttempt(
  rec: Omit<AttemptRecord, "ts"> & { ts?: number }
): ProgressState {
  const state = loadProgress();
  const entry: AttemptRecord = {
    questionId: rec.questionId,
    examType: rec.examType,
    module: rec.module,
    correct: rec.correct,
    timeMs: rec.timeMs,
    ts: rec.ts ?? Date.now(),
  };
  const next = [...state.attempts, entry];
  // Drop oldest if we've exceeded the cap.
  const trimmed =
    next.length > MAX_ATTEMPTS ? next.slice(next.length - MAX_ATTEMPTS) : next;
  const out = { attempts: trimmed };
  saveProgress(out);
  return out;
}

export function clearProgress(): void {
  if (!isBrowser()) return;
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

// ── Derived stats ──────────────────────────────────────────────────────

export interface ModuleStat {
  code: string;
  label: string;
  answered: number;
  correct: number;
  accuracy: number; // 0..100, 0 when answered === 0
}

export interface ProgressStats {
  totalAnswered: number;
  totalCorrect: number;
  accuracy: number; // 0..100
  /** Consecutive correct answers ending at the most recent attempt. */
  currentStreak: number;
  /** Longest run of consecutive correct answers in the log. */
  bestStreak: number;
  /** Mean time per answered question in ms (only counts timed attempts). */
  avgTimeMs: number;
  byModule: ModuleStat[];
  byExam: ModuleStat[];
  /** Number of distinct calendar days with at least one attempt. */
  activeDayCount: number;
  /** Consecutive calendar days ending today with at least one attempt. */
  dayStreak: number;
  /** Whether the user has any recorded progress at all. */
  hasData: boolean;
}

function dayKey(ts: number): string {
  const d = new Date(ts);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate()
  ).padStart(2, "0")}`;
}

export function computeStats(state: ProgressState): ProgressStats {
  const attempts = state.attempts;
  if (attempts.length === 0) {
    return {
      totalAnswered: 0,
      totalCorrect: 0,
      accuracy: 0,
      currentStreak: 0,
      bestStreak: 0,
      avgTimeMs: 0,
      byModule: [],
      byExam: [],
      activeDayCount: 0,
      dayStreak: 0,
      hasData: false,
    };
  }

  const totalAnswered = attempts.length;
  const totalCorrect = attempts.filter((a) => a.correct).length;
  const accuracy = Math.round((totalCorrect / totalAnswered) * 100);

  // Consecutive-correct streak ending at the most recent attempt.
  let currentStreak = 0;
  for (let i = attempts.length - 1; i >= 0; i--) {
    if (attempts[i].correct) currentStreak++;
    else break;
  }
  // Best-ever run of consecutive correct.
  let bestStreak = 0;
  let run = 0;
  for (const a of attempts) {
    if (a.correct) {
      run++;
      if (run > bestStreak) bestStreak = run;
    } else {
      run = 0;
    }
  }

  // Average time per question (only over timed attempts).
  const timed = attempts.filter(
    (a): a is AttemptRecord & { timeMs: number } =>
      typeof a.timeMs === "number" && a.timeMs > 0
  );
  const avgTimeMs =
    timed.length > 0
      ? Math.round(timed.reduce((s, a) => s + a.timeMs, 0) / timed.length)
      : 0;

  // Group by module and exam.
  const byModule = groupAccuracy(attempts, (a) => a.module, MODULE_LABELS);
  const byExam = groupAccuracy(attempts, (a) => a.examType, undefined);

  // Day stats.
  const days = new Set(attempts.map((a) => dayKey(a.ts)));
  const activeDayCount = days.size;
  const dayStreak = computeDayStreak(days);

  return {
    totalAnswered,
    totalCorrect,
    accuracy,
    currentStreak,
    bestStreak,
    avgTimeMs,
    byModule,
    byExam,
    activeDayCount,
    dayStreak,
    hasData: true,
  };
}

function groupAccuracy(
  attempts: AttemptRecord[],
  keyFn: (a: AttemptRecord) => string,
  labels: Record<string, string> | undefined
): ModuleStat[] {
  const buckets = new Map<
    string,
    { answered: number; correct: number }
  >();
  for (const a of attempts) {
    const k = keyFn(a) || "general";
    const b = buckets.get(k) ?? { answered: 0, correct: 0 };
    b.answered++;
    if (a.correct) b.correct++;
    buckets.set(k, b);
  }
  return Array.from(buckets.entries())
    .map(([code, b]) => ({
      code,
      label: labels?.[code] ?? (code ? code.charAt(0).toUpperCase() + code.slice(1) : "General"),
      answered: b.answered,
      correct: b.correct,
      accuracy: Math.round((b.correct / b.answered) * 100),
    }))
    .sort((a, b) => b.answered - a.answered);
}

function computeDayStreak(days: Set<string>): number {
  if (days.size === 0) return 0;
  // Walk backwards from today; count consecutive days present in the set.
  let streak = 0;
  const cursor = new Date();
  // If today isn't a practice day but yesterday is, still count from
  // yesterday so an early-morning user keeps their streak.
  if (!days.has(dayKey(cursor.getTime()))) {
    cursor.setDate(cursor.getDate() - 1);
    if (!days.has(dayKey(cursor.getTime()))) return 0;
  }
  while (days.has(dayKey(cursor.getTime()))) {
    streak++;
    cursor.setDate(cursor.getDate() - 1);
  }
  return streak;
}

/** Format milliseconds as M:SS for the dashboard's "Avg Time / Q" card. */
export function formatMSS(ms: number): string {
  if (!ms || ms <= 0) return "—";
  const totalSec = Math.round(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/**
 * Build the RadarPoint[] the RadarChartSVG expects, one axis per known
 * module, ordered by RADAR_AXIS_ORDER. Modules with no attempts yet are
 * rendered at 0 so the chart still shows the full pentagon shape.
 */
export interface RadarPoint {
  axis: string;
  v: number;
  answered: number;
  /** Canonical module code — used for deep-linking into topic-filtered practice. */
  code: string;
}

export function buildRadarData(stats: ProgressStats): RadarPoint[] {
  const accuracyByCode = new Map(stats.byModule.map((m) => [m.code, m]));
  const out: RadarPoint[] = [];
  for (const code of RADAR_AXIS_ORDER) {
    const m = accuracyByCode.get(code);
    out.push({
      axis: moduleLabel(code),
      v: m ? m.accuracy : 0,
      answered: m ? m.answered : 0,
      code,
    });
  }
  // Include any module we've seen that isn't in the canonical order
  // (future-proofs against new exam modules).
  for (const m of stats.byModule) {
    if (!RADAR_AXIS_ORDER.includes(m.code)) {
      out.push({ axis: m.label, v: m.accuracy, answered: m.answered, code: m.code });
    }
  }
  return out;
}
