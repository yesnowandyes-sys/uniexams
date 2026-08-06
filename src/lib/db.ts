import Database from "better-sqlite3";
import path from "path";
import fs from "fs";

const DB_PATH = path.join(process.cwd(), "data", "questions.db");

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (_db) return _db;

  // Ensure data directory exists
  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  _db = new Database(DB_PATH);
  _db.pragma("journal_mode = WAL");
  _db.pragma("foreign_keys = ON");

  initSchema(_db);
  return _db;
}

/**
 * Schema overview
 * ===============
 *
 * The `questions` table is the single canonical store for both past-paper
 * corpus questions (`source = 'corpus'`) and LLM-generated questions
 * (`source = 'generated'`). Merging the two into one table keeps the
 * website's query path simple — `queryQuestions()` doesn't need to know
 * whether a row came from the import-corpus script or from the nightly
 * generation pipeline.
 *
 * Pipeline-provenance tables (touched only by the generation pipeline,
 * never by the user-facing query path):
 *
 * - `generation_attempts` — every candidate produced by the generator
 *   (GLM-5.2 primary / Haiku fallback). Rows record the model, prompt
 *   hash, candidate body, and final accept/reject status. One row per
 *   candidate; survivors graduate into `questions` with `source='generated'`.
 * - `quality_reviews` — one row per (attempt, gate) pair. Gates are the
 *   4-gate stack from the strategy doc (calculator, solver, sympy,
 *   rubric) plus the subject-specific add-ons (chem_stoich, bio_judge).
 * - `coverage_targets` — operator-editable target share per
 *   (module, topic, difficulty); drives the nightly topic picker.
 * - `pattern_files` — registry of the Opus-produced per-topic pattern
 *   files (style guide, distractor catalogue, insight scenarios).
 *
 * Idempotency: `CREATE TABLE IF NOT EXISTS` handles fresh creates and
 * already-migrated DBs. `migrateQuestionsTable` handles the
 * additive-column case on DBs that predate this migration (it inspects
 * `PRAGMA table_info(questions)` and only ALTERs missing columns).
 */
function initSchema(db: Database.Database) {
  // Step 1: create tables (skipped if they already exist). Only the
  // indexes that do not depend on the new additive columns are safe to
  // create here — the source-column index is created after migration.
  db.exec(`
    CREATE TABLE IF NOT EXISTS questions (
      id              TEXT PRIMARY KEY,
      exam_type       TEXT NOT NULL,          -- esat | engaa | nsaa | nsaa_s2 | tmua
      year            TEXT,                   -- e.g. "2020", "specimen"
      paper           TEXT,                   -- e.g. "ESAT", "ENGAA", "TMUA"
      module          TEXT,                   -- e.g. "biology", "chemistry", "maths1"
      section         TEXT,                   -- e.g. "s1", "s2", "p1", "p2"
      subject         TEXT,                   -- for NSAA S2: biology/chemistry/physics
      part            TEXT,                   -- for NSAA S2: part letter
      question_number INTEGER NOT NULL,
      question_text   TEXT NOT NULL,
      question_images TEXT DEFAULT '[]',      -- JSON array of image paths
      options         TEXT NOT NULL,          -- JSON: {"A": "...", "B": "...", ...}
      correct_answer  TEXT NOT NULL,          -- letter, e.g. "D"
      explanation     TEXT DEFAULT '',
      explanation_images TEXT DEFAULT '[]',   -- JSON array
      screenshot      TEXT DEFAULT '',
      enrichment      TEXT,                   -- JSON: {status, model, markdown, difficulty, topics, ...}
      metadata        TEXT DEFAULT '{}',      -- JSON: flexible extra fields
      source                     TEXT NOT NULL DEFAULT 'corpus',  -- 'corpus' | 'generated'
      generated_from_template_id TEXT,                            -- pattern_files.id for generated rows
      difficulty_score           REAL,                            -- structural difficulty (0..1); NULL for corpus
      created_at      TEXT DEFAULT (datetime('now')),
      updated_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_questions_exam_type ON questions(exam_type);
    CREATE INDEX IF NOT EXISTS idx_questions_year ON questions(year);
    CREATE INDEX IF NOT EXISTS idx_questions_module ON questions(module);
    CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject);

    CREATE TABLE IF NOT EXISTS attempt_stats (
      question_id     TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
      times_answered  INTEGER DEFAULT 0,
      times_correct   INTEGER DEFAULT 0,
      avg_time_ms     REAL DEFAULT 0
    );

    -- Every candidate produced by the nightly generator. Accepted rows
    -- also graduate into the questions table with source='generated';
    -- rejected rows stay here for pipeline analytics.
    CREATE TABLE IF NOT EXISTS generation_attempts (
      id              TEXT PRIMARY KEY,
      batch_id        TEXT NOT NULL,          -- groups candidates from one nightly run
      spec_topic      TEXT NOT NULL,          -- e.g. "MM1.4" — drives coverage tracking
      model           TEXT NOT NULL,          -- e.g. "glm-5.2", "haiku-4-5"
      prompt_hash     TEXT,                   -- sha256 of the rendered prompt, for reproducibility
      question_text   TEXT NOT NULL,
      options         TEXT NOT NULL,          -- JSON: {"A": "...", ...}
      correct_answer  TEXT NOT NULL,
      explanation     TEXT DEFAULT '',
      status          TEXT NOT NULL DEFAULT 'pending',  -- pending | accepted | rejected
      reject_reason   TEXT,                   -- short machine-readable tag, e.g. "calculator_gate"
      question_id     TEXT,                   -- set when status='accepted' → questions.id
      created_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_attempts_batch    ON generation_attempts(batch_id);
    CREATE INDEX IF NOT EXISTS idx_attempts_topic    ON generation_attempts(spec_topic);
    CREATE INDEX IF NOT EXISTS idx_attempts_status   ON generation_attempts(status);
    CREATE INDEX IF NOT EXISTS idx_attempts_model    ON generation_attempts(model);

    -- One row per (attempt, gate). Gates: calculator | solver | sympy |
    -- rubric | chem_stoich | bio_judge. An attempt is accepted only if
    -- every gate it ran returned passed=1.
    CREATE TABLE IF NOT EXISTS quality_reviews (
      id              TEXT PRIMARY KEY,
      attempt_id      TEXT NOT NULL REFERENCES generation_attempts(id) ON DELETE CASCADE,
      gate            TEXT NOT NULL,
      passed          INTEGER NOT NULL,       -- 0 | 1
      score           REAL,                   -- gate-native (e.g. rubric 1..5); NULL for boolean gates
      reason          TEXT,                   -- short failure explanation
      reviewer_model  TEXT,                   -- model that ran this gate (NULL for deterministic gates)
      metadata        TEXT DEFAULT '{}',      -- JSON: gate-specific payload
      created_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_reviews_attempt ON quality_reviews(attempt_id);
    CREATE INDEX IF NOT EXISTS idx_reviews_gate    ON quality_reviews(gate);

    -- Target share of generated questions per (module, topic, difficulty).
    -- Drives the nightly topic picker. Edited by operators; not written
    -- by automated runs.
    CREATE TABLE IF NOT EXISTS coverage_targets (
      id              TEXT PRIMARY KEY,
      module          TEXT NOT NULL,
      topic           TEXT NOT NULL,
      difficulty      TEXT NOT NULL,          -- Easy | Medium | Hard | Very Hard
      target_pct      REAL NOT NULL,          -- desired share (0..100) of generated questions in this cell
      notes           TEXT DEFAULT '',
      updated_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_coverage_unique
      ON coverage_targets(module, topic, difficulty);

    -- Registry of Opus-produced per-topic pattern files. One row per
    -- (spec_topic, version). References questions.generated_from_template_id.
    CREATE TABLE IF NOT EXISTS pattern_files (
      id                          TEXT PRIMARY KEY,
      spec_topic                  TEXT NOT NULL,
      style_guide_path            TEXT NOT NULL,
      distractor_catalogue_path   TEXT NOT NULL,
      insight_scenarios_path      TEXT NOT NULL,
      version                     TEXT NOT NULL,
      generated_at                TEXT NOT NULL,
      model                       TEXT,
      notes                       TEXT DEFAULT ''
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_pattern_files_unique
      ON pattern_files(spec_topic, version);
  `);

  // Step 2: additive column migration. Must run before any index that
  // references the new columns is created (e.g. idx_questions_source).
  migrateQuestionsTable(db);

  // Step 3: indexes that depend on the migrated columns.
  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_questions_source ON questions(source);
  `);
}

/**
 * Additive migration: ensure `questions` has the columns introduced by
 * the generation pipeline (source, generated_from_template_id,
 * difficulty_score). Skips columns that already exist, so it is safe to
 * call on every getDb() — including against DBs created fresh by
 * import-corpus.ts (which already includes the columns in CREATE).
 *
 * SQLite does not support `ALTER TABLE ADD COLUMN IF NOT EXISTS`, so we
 * introspect via PRAGMA table_info before issuing each ALTER.
 */
function migrateQuestionsTable(db: Database.Database): void {
  const cols = db.prepare("PRAGMA table_info(questions)").all() as Array<{ name: string }>;
  const present = new Set(cols.map((c) => c.name));

  const additions: Array<{ name: string; sql: string }> = [
    {
      name: "source",
      sql: `ALTER TABLE questions ADD COLUMN source TEXT NOT NULL DEFAULT 'corpus'`,
    },
    {
      name: "generated_from_template_id",
      sql: `ALTER TABLE questions ADD COLUMN generated_from_template_id TEXT`,
    },
    {
      name: "difficulty_score",
      sql: `ALTER TABLE questions ADD COLUMN difficulty_score REAL`,
    },
  ];

  for (const { name, sql } of additions) {
    if (!present.has(name)) {
      db.exec(sql);
    }
  }

  // Materialize the default for any pre-migration rows. ADD COLUMN with
  // DEFAULT makes SQLite *return* 'corpus' for these rows at read time,
  // but the on-disk value is still NULL until rewritten. The explicit
  // UPDATE pins the value so downstream tools (e.g. dumps, copies) see
  // 'corpus' rather than NULL.
  db.exec(`UPDATE questions SET source = 'corpus' WHERE source IS NULL`);
}

// Types
export type QuestionSource = "corpus" | "generated";

export interface Question {
  id: string;
  exam_type: string;
  year: string;
  paper: string;
  module: string;
  section: string;
  subject: string;
  part: string;
  question_number: number;
  question_text: string;
  question_images: string[];
  options: Record<string, string>;
  correct_answer: string;
  explanation: string;
  explanation_images: string[];
  screenshot: string;
  enrichment: Enrichment | null;
  metadata: Record<string, unknown>;
  source: QuestionSource;                   // 'corpus' | 'generated'
  generated_from_template_id: string | null; // pattern_files.id when source='generated'
  difficulty_score: number | null;           // structural 0..1; NULL for corpus
  created_at: string;
  updated_at: string;
}

/**
 * A generation candidate tracked by the nightly pipeline. Accepted
 * candidates graduate into `questions` with source='generated'.
 */
export interface GenerationAttempt {
  id: string;
  batch_id: string;
  spec_topic: string;
  model: string;
  prompt_hash: string | null;
  question_text: string;
  options: Record<string, string>;
  correct_answer: string;
  explanation: string;
  status: "pending" | "accepted" | "rejected";
  reject_reason: string | null;
  question_id: string | null; // set when status='accepted'
  created_at: string;
}

/** One row per (attempt, gate) in the 4-gate quality stack. */
export interface QualityReview {
  id: string;
  attempt_id: string;
  gate: string; // calculator | solver | sympy | rubric | chem_stoich | bio_judge
  passed: boolean;
  score: number | null;
  reason: string | null;
  reviewer_model: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

/** Operator-editable target share per (module, topic, difficulty). */
export interface CoverageTarget {
  id: string;
  module: string;
  topic: string;
  difficulty: string; // Easy | Medium | Hard | Very Hard
  target_pct: number;
  notes: string;
  updated_at: string;
}

/** Registry row for an Opus-produced per-topic pattern file bundle. */
export interface PatternFile {
  id: string;
  spec_topic: string;
  style_guide_path: string;
  distractor_catalogue_path: string;
  insight_scenarios_path: string;
  version: string;
  generated_at: string;
  model: string | null;
  notes: string;
}

export interface Enrichment {
  status?: string;
  model?: string;
  enriched_at?: string;
  markdown?: string;
  difficulty?: string;
  topics?: string[];
}

export interface QuestionFilters {
  exam_type?: string;
  year?: string;
  module?: string;
  subject?: string;
  section?: string;
  // Enrichment-derived filters (require enrichment JSON to be populated).
  difficulty?: string; // Easy | Medium | Hard | Very Hard
  topic?: string; // substring match against topic_code/topic_name/content_code
  enriched_only?: boolean; // only return questions with enrichment data
  verified_only?: boolean; // only return questions that passed verification
  limit?: number;
  offset?: number;
  random?: boolean;
}

/**
 * Whitelisted difficulty labels that the enrichment pipeline emits.
 * Inputs are matched case-insensitively against this set so we can reject
 * typos early instead of silently returning zero results.
 */
export const DIFFICULTY_LABELS = ["Easy", "Medium", "Hard", "Very Hard"] as const;
const DIFFICULTY_SET = new Set(DIFFICULTY_LABELS.map((d) => d.toLowerCase()));

function normalizeDifficulty(input: string | undefined): string | undefined {
  if (!input) return undefined;
  const lower = input.trim().toLowerCase();
  // Accept common aliases.
  if (lower === "vh" || lower === "very-hard" || lower === "veryhard") return "Very Hard";
  if (!DIFFICULTY_SET.has(lower)) return undefined;
  if (lower === "very hard") return "Very Hard";
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

// Query functions
/**
 * Build the WHERE clause + bind params shared by queryQuestions / countQuestions.
 * Enrichment-derived filters (difficulty, topic, enriched_only) operate on the
 * JSON `enrichment` column using SQLite's json_extract. These filters silently
 * match nothing when no enrichment has been loaded yet — callers should check
 * `enriched_only` semantics at the API layer if they want to distinguish.
 */
/**
 * SQL CASE expression that derives the effective module from the raw column,
 * the subject column, and the enrichment topic_classification — mirroring
 * deriveEffectiveModule(). Used in WHERE/GROUP BY so legacy exam questions
 * (which have module="" in the DB) can be filtered and counted by module.
 */
const EFFECTIVE_MODULE_SQL = `(
  CASE
    WHEN module IS NOT NULL AND TRIM(module) != '' THEN module
    WHEN subject IS NOT NULL AND LOWER(TRIM(subject)) IN ('biology','chemistry','physics') THEN LOWER(TRIM(subject))
    WHEN enrichment IS NOT NULL AND json_extract(enrichment, '$.topic_classification.module') IS NOT NULL THEN
      CASE
        WHEN LOWER(json_extract(enrichment, '$.topic_classification.module')) LIKE '%biology%' THEN 'biology'
        WHEN LOWER(json_extract(enrichment, '$.topic_classification.module')) LIKE '%chem%' THEN 'chemistry'
        WHEN LOWER(json_extract(enrichment, '$.topic_classification.module')) LIKE '%physics%' THEN 'physics'
        WHEN LOWER(json_extract(enrichment, '$.topic_classification.module')) LIKE '%mathematics 2%'
             OR LOWER(json_extract(enrichment, '$.topic_classification.module')) LIKE '%math 2%'
             OR LOWER(json_extract(enrichment, '$.topic_classification.module')) = 'm2' THEN 'maths2'
        WHEN LOWER(json_extract(enrichment, '$.topic_classification.module')) LIKE '%mathematics%'
             OR LOWER(json_extract(enrichment, '$.topic_classification.module')) LIKE '%math 1%'
             OR LOWER(json_extract(enrichment, '$.topic_classification.module')) = 'm1' THEN 'maths1'
        ELSE ''
      END
    ELSE ''
  END
)`;

/**
 * SQL CASE expression that derives the effective difficulty label for a
 * question, mirroring EFFECTIVE_MODULE_SQL. Corpus questions carry their
 * label in enrichment.difficulty_category; generated questions carry no
 * enrichment but do have a numeric 1-5 difficulty_score (the generator's
 * self-assessment), bucketed here with the same bands reviewer.py's
 * DIFFICULTY_BAND_MAP uses (1-2 easy, 3 medium, 4 hard, 5 very hard) so
 * generated questions are filterable/countable by difficulty too.
 */
const EFFECTIVE_DIFFICULTY_SQL = `(
  CASE
    WHEN enrichment IS NOT NULL AND json_extract(enrichment, '$.status') = 'success'
         AND json_extract(enrichment, '$.difficulty_category') IS NOT NULL
      THEN json_extract(enrichment, '$.difficulty_category')
    WHEN source = 'generated' AND difficulty_score IS NOT NULL THEN
      CASE
        WHEN difficulty_score <= 2 THEN 'Easy'
        WHEN difficulty_score = 3 THEN 'Medium'
        WHEN difficulty_score = 4 THEN 'Hard'
        ELSE 'Very Hard'
      END
    ELSE NULL
  END
)`;

function buildWhereClause(filters: QuestionFilters): { where: string; params: unknown[] } {
  const conditions: string[] = [];
  const params: unknown[] = [];

  if (filters.exam_type) {
    conditions.push("exam_type = ?");
    params.push(filters.exam_type);
  }
  if (filters.year) {
    conditions.push("year = ?");
    params.push(filters.year);
  }
  if (filters.module) {
    conditions.push(`${EFFECTIVE_MODULE_SQL} = ?`);
    params.push(filters.module);
  }
  if (filters.subject) {
    conditions.push("subject = ?");
    params.push(filters.subject);
  }
  if (filters.section) {
    conditions.push("section = ?");
    params.push(filters.section);
  }

  // Enrichment-derived filters all imply status='success' so partial / failed
  // enrichments never leak into filtered results. This keeps topic and
  // enriched_only on the same footing. Difficulty is excluded here — it has
  // its own generated-question fallback via EFFECTIVE_DIFFICULTY_SQL below.
  const usesEnrichment = filters.enriched_only || Boolean(filters.topic);
  if (usesEnrichment) {
    conditions.push("enrichment IS NOT NULL");
    conditions.push("json_extract(enrichment, '$.status') = 'success'");
  }

  if (filters.verified_only) {
    // A question counts as verified if EITHER:
    //   (a) its enrichment JSON records a successful verification (corpus path),
    //   OR
    //   (b) it was produced by the generate-then-verify pipeline
    //       (source = 'generated'), which only inserts a question after it has
    //       passed every quality gate (calculator/sympy/solver/reviewer/...).
    // Without the source clause, the entire generated pool is invisible to the
    // site because generated rows carry no enrichment JSON.
    conditions.push(
      "(json_extract(enrichment, '$.verification.verified') = 1 OR source = 'generated')",
    );
  }

  if (filters.difficulty) {
    const normalized = normalizeDifficulty(filters.difficulty);
    if (!normalized) {
      // Unknown difficulty label — force no matches rather than silently
      // returning the whole corpus.
      conditions.push("1 = 0");
    } else {
      conditions.push(`${EFFECTIVE_DIFFICULTY_SQL} = ?`);
      params.push(normalized);
    }
  }

  if (filters.topic) {
    // Substring match across the topic classification fields so callers can
    // pass either a code (e.g. "MM1.4") or a human label (e.g. "Algebra").
    const like = `%${filters.topic}%`;
    conditions.push(
      `(
        IFNULL(json_extract(enrichment, '$.topic_classification.topic_code'), '') LIKE ? OR
        IFNULL(json_extract(enrichment, '$.topic_classification.topic_name'), '') LIKE ? OR
        IFNULL(json_extract(enrichment, '$.topic_classification.content_code'), '') LIKE ? OR
        IFNULL(json_extract(enrichment, '$.topic_classification.module_code'), '') LIKE ? OR
        IFNULL(json_extract(enrichment, '$.topic_classification.module'), '') LIKE ?
      )`
    );
    params.push(like, like, like, like, like);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";
  return { where, params };
}

export function queryQuestions(filters: QuestionFilters = {}): Question[] {
  const db = getDb();
  const { where, params } = buildWhereClause(filters);
  const order = filters.random ? "ORDER BY RANDOM()" : "ORDER BY exam_type, year, module, question_number";
  const limit = filters.limit ?? 50;
  const offset = filters.offset ?? 0;

  const rows = db.prepare(
    `SELECT * FROM questions ${where} ${order} LIMIT ? OFFSET ?`
  ).all(...params, limit, offset) as RawQuestionRow[];

  return rows.map(rowToQuestion);
}

export function getQuestionById(id: string): Question | null {
  const db = getDb();
  const row = db.prepare("SELECT * FROM questions WHERE id = ?").get(id) as RawQuestionRow | undefined;
  return row ? rowToQuestion(row) : null;
}

export function countQuestions(filters: QuestionFilters = {}): number {
  const db = getDb();
  const { where, params } = buildWhereClause(filters);
  const result = db.prepare(`SELECT COUNT(*) as count FROM questions ${where}`).get(...params) as { count: number };
  return result.count;
}

/**
 * Record an attempt against a question, updating the per-question attempt
 * aggregate. Inserts the row if missing. Idempotent within a transaction —
 * safe to call from the answer-scoring API on every submission.
 */
export function recordAttempt(
  questionId: string,
  isCorrect: boolean,
  timeMs?: number
): void {
  const db = getDb();
  // SQLite doesn't have native UPSERT-on-conflict for the running-mean case,
  // so we update times_answered/times_correct with a coalesced increment and
  // fold the new time into avg_time_ms as a running average.
  const row = db
    .prepare("SELECT times_answered, times_correct, avg_time_ms FROM attempt_stats WHERE question_id = ?")
    .get(questionId) as
    | { times_answered: number; times_correct: number; avg_time_ms: number }
    | undefined;

  const prev = row ?? { times_answered: 0, times_correct: 0, avg_time_ms: 0 };
  const nextAnswered = prev.times_answered + 1;
  const nextCorrect = prev.times_correct + (isCorrect ? 1 : 0);
  const nextAvg =
    typeof timeMs === "number" && timeMs >= 0
      ? (prev.avg_time_ms * prev.times_answered + timeMs) / nextAnswered
      : prev.avg_time_ms;

  db.prepare(
    `INSERT INTO attempt_stats (question_id, times_answered, times_correct, avg_time_ms)
     VALUES (?, ?, ?, ?)
     ON CONFLICT(question_id) DO UPDATE SET
       times_answered = excluded.times_answered,
       times_correct  = excluded.times_correct,
       avg_time_ms    = excluded.avg_time_ms`
  ).run(questionId, nextAnswered, nextCorrect, nextAvg);
}

export function getExamStats(): Record<string, { count: number; years: string[]; modules: string[] }> {
  const db = getDb();
  const rows = db.prepare(`
    SELECT exam_type,
           COUNT(*) as count,
           GROUP_CONCAT(DISTINCT year) as years,
           GROUP_CONCAT(DISTINCT ${EFFECTIVE_MODULE_SQL}) as modules
    FROM questions
    GROUP BY exam_type
  `).all() as { exam_type: string; count: number; years: string; modules: string }[];

  const stats: Record<string, { count: number; years: string[]; modules: string[] }> = {};
  for (const row of rows) {
    const modules = row.modules
      ? row.modules.split(",").filter((m) => m.trim() !== "")
      : [];
    stats[row.exam_type] = {
      count: row.count,
      years: row.years ? row.years.split(",") : [],
      modules,
    };
  }
  return stats;
}

/**
 * Aggregated facets derived from the enrichment column. Useful for driving
 * filter UIs and for the /api/questions/stats endpoint. `enriched_count` and
 * `by_topic` only include questions whose enrichment status is 'success';
 * `by_difficulty` also folds in generated questions via difficulty_score
 * (see EFFECTIVE_DIFFICULTY_SQL).
 */
export interface EnrichmentFacets {
  enriched_count: number;
  by_difficulty: Record<string, number>;
  by_topic: Array<{ code: string; name: string; count: number }>;
}

export function getEnrichmentFacets(): EnrichmentFacets {
  const db = getDb();
  const enrichedCount = db
    .prepare(
      `SELECT COUNT(*) AS c FROM questions
       WHERE enrichment IS NOT NULL AND json_extract(enrichment, '$.status') = 'success'`
    )
    .get() as { c: number };

  const diffRows = db
    .prepare(
      `SELECT IFNULL(${EFFECTIVE_DIFFICULTY_SQL}, 'Unknown') AS difficulty,
              COUNT(*) AS c
       FROM questions
       WHERE (enrichment IS NOT NULL AND json_extract(enrichment, '$.status') = 'success')
          OR (source = 'generated' AND difficulty_score IS NOT NULL)
       GROUP BY difficulty
       ORDER BY difficulty`
    )
    .all() as Array<{ difficulty: string; c: number }>;

  const by_difficulty: Record<string, number> = {};
  for (const r of diffRows) by_difficulty[r.difficulty] = r.c;

  const topicRows = db
    .prepare(
      `SELECT IFNULL(json_extract(enrichment, '$.topic_classification.topic_code'), '') AS code,
              IFNULL(json_extract(enrichment, '$.topic_classification.topic_name'), '') AS name,
              COUNT(*) AS c
       FROM questions
       WHERE enrichment IS NOT NULL
         AND json_extract(enrichment, '$.status') = 'success'
         AND json_extract(enrichment, '$.topic_classification.topic_code') IS NOT NULL
       GROUP BY code, name
       ORDER BY c DESC`
    )
    .all() as Array<{ code: string; name: string; c: number }>;

  const by_topic = topicRows
    .filter((r) => r.code)
    .map((r) => ({ code: r.code, name: r.name || r.code, count: r.c }));

  return {
    enriched_count: enrichedCount.c,
    by_difficulty,
    by_topic,
  };
}

// Internal helpers
interface RawQuestionRow {
  id: string;
  exam_type: string;
  year: string | null;
  paper: string | null;
  module: string | null;
  section: string | null;
  subject: string | null;
  part: string | null;
  question_number: number;
  question_text: string;
  question_images: string | null;
  options: string;
  correct_answer: string;
  explanation: string | null;
  explanation_images: string | null;
  screenshot: string | null;
  enrichment: string | null;
  metadata: string | null;
  source: string | null;
  generated_from_template_id: string | null;
  difficulty_score: number | null;
  created_at: string;
  updated_at: string;
}

/**
 * Derive an effective module code when the `module` column is empty.
 *
 * Legacy corpus exams (engaa, nsaa, nsaa_s2, tmua) were imported before the
 * module column was introduced, so they have module="" in the DB. The
 * enrichment pipeline DID classify them, so we can recover the module from
 * either:
 *   1. the `subject` column (nsaa_s2 sets subject=biology|chemistry|physics), or
 *   2. the enrichment.topic_classification.module JSON field (engaa/nsaa/tmua).
 *
 * Returns the original module if it is already non-empty.
 */
function deriveEffectiveModule(
  rawModule: string | null,
  subject: string | null,
  enrichmentRaw: string | null
): string {
  const mod = (rawModule ?? "").trim();
  if (mod) return mod;

  // nsaa_s2 stores the science in `subject`.
  const subj = (subject ?? "").trim().toLowerCase();
  if (subj === "biology" || subj === "chemistry" || subj === "physics") {
    return subj;
  }

  // Fall back to enrichment topic_classification.module, normalised to our
  // canonical codes.
  if (enrichmentRaw) {
    try {
      const en = JSON.parse(enrichmentRaw) as Enrichment & {
        topic_classification?: { module?: string };
      };
      const label = (en.topic_classification?.module ?? "").toLowerCase();
      if (label) {
        if (label.includes("biology")) return "biology";
        if (label.includes("chem")) return "chemistry";
        if (label.includes("physics")) return "physics";
        if (label.includes("mathematics 2") || label.includes("math 2") || label === "m2") return "maths2";
        if (label.includes("mathematics 1") || label.includes("math 1") || label === "m1" || label.includes("mathematics")) return "maths1";
      }
    } catch {
      // enrichment JSON is malformed; skip
    }
  }

  return "";
}

function rowToQuestion(row: RawQuestionRow): Question {
  return {
    id: row.id,
    exam_type: row.exam_type,
    year: row.year ?? "",
    paper: row.paper ?? "",
    module: deriveEffectiveModule(row.module, row.subject, row.enrichment),
    section: row.section ?? "",
    subject: row.subject ?? "",
    part: row.part ?? "",
    question_number: row.question_number,
    question_text: row.question_text,
    question_images: JSON.parse(row.question_images ?? "[]"),
    options: JSON.parse(row.options),
    correct_answer: row.correct_answer,
    explanation: row.explanation ?? "",
    explanation_images: JSON.parse(row.explanation_images ?? "[]"),
    screenshot: row.screenshot ?? "",
    enrichment: row.enrichment ? JSON.parse(row.enrichment) : null,
    metadata: row.metadata ? JSON.parse(row.metadata) : {},
    source: (row.source as QuestionSource) ?? "corpus",
    generated_from_template_id: row.generated_from_template_id ?? null,
    difficulty_score: row.difficulty_score ?? null,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}
