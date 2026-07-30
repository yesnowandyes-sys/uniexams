/**
 * Import script: reads all corpus JSON files and populates the SQLite database.
 *
 * Usage:
 *   npx tsx scripts/import-corpus.ts
 *
 * Or via npm:
 *   npm run import-corpus
 */
import Database from "better-sqlite3";
import fs from "fs";
import path from "path";

const CORPUS_DIR = path.join(process.cwd(), "corpus", "json");
const ENRICHED_DIRS = [
  path.join(process.cwd(), "enriched-output", "opus-trial"),
  path.join(process.cwd(), "enriched-output", "opus-batch"),
  path.join(process.cwd(), "enriched-output", "glm-trial"),
  path.join(process.cwd(), "enriched-output", "glm-trial-v2"),
];
const DB_PATH = path.join(process.cwd(), "data", "questions.db");

interface CorpusQuestion {
  id: string;
  year?: string;
  paper?: string;
  module?: string;
  section?: string;
  subject?: string;
  part?: string;
  question_number?: number;
  question_text?: string;
  question_images?: string[];
  screenshot?: string;
  explanation_screenshot?: string;
  options?: Record<string, string>;
  options_detailed?: Record<string, { text: string; math_alt?: string[]; plain_text?: string }>;
  options_latex?: Record<string, string>;
  correct_answer?: string;
  correct_answer_raw?: string;
  correct_answer_plain?: string;
  correct_answer_images?: string[];
  explanation?: string;
  explanation_images?: string[];
  has_diagram?: boolean;
  diagram_images?: string[];
  raw_text?: string;
  enrichment?: unknown;
  extracted_at?: string;
}

interface CorpusFile {
  module?: string;
  label?: string;
  total_questions?: number;
  source_file?: string;
  paper_type?: string;
  year?: string;
  section?: string;
  paper?: string;
  specimen?: boolean;
  subject?: string;
  questions: CorpusQuestion[];
  extracted_at?: string;
}

function normalizeYear(raw: unknown): string {
  if (typeof raw === "number") return String(raw);
  if (typeof raw === "string") {
    // Handle "2020.0" -> "2020"
    const num = Number(raw);
    if (!isNaN(num) && raw.includes(".")) return String(Math.round(num));
    return raw;
  }
  return "";
}

function determineExamType(filePath: string): string {
  if (filePath.includes("/esat/")) return "esat";
  if (filePath.includes("/engaa/")) return "engaa";
  if (filePath.includes("/nsaa_s2/")) return "nsaa_s2";
  if (filePath.includes("/nsaa/")) return "nsaa";
  if (filePath.includes("/tmua/")) return "tmua";
  return "unknown";
}

function normalizeQuestion(fileData: CorpusFile, q: CorpusQuestion, filePath: string) {
  const examType = determineExamType(filePath);

  // Derive section from file data or question
  let section = q.section ?? fileData.section ?? "";
  if (!section) {
    // Try to infer from filename
    const fname = path.basename(filePath);
    if (fname.includes("_s1") || fname.includes("s1")) section = "s1";
    else if (fname.includes("_s2") || fname.includes("s2")) section = "s2";
    else if (fname.includes("_p1") || fname.includes("p1")) section = "p1";
    else if (fname.includes("_p2") || fname.includes("p2")) section = "p2";
  }

  // Normalize options: prefer options, fall back to options_latex
  let options = q.options ?? {};
  if (Object.keys(options).length === 0 && q.options_latex) {
    options = q.options_latex;
  }

  // Collect images
  const questionImages = q.question_images ?? q.diagram_images ?? [];
  const explanationImages = q.explanation_images ?? [];

  // Subject for NSAA S2
  const subject = q.subject ?? fileData.subject ?? "";

  // Enrichment
  const enrichment = q.enrichment ? JSON.stringify(q.enrichment) : null;

  // Metadata - store extra fields for flexibility
  const metadata = JSON.stringify({
    has_diagram: q.has_diagram ?? false,
    raw_text: q.raw_text ?? "",
    correct_answer_raw: q.correct_answer_raw ?? "",
    correct_answer_plain: q.correct_answer_plain ?? "",
    correct_answer_images: q.correct_answer_images ?? [],
    explanation_screenshot: q.explanation_screenshot ?? "",
    extracted_at: q.extracted_at ?? fileData.extracted_at ?? "",
    source_file: fileData.source_file ?? "",
    label: fileData.label ?? "",
    specimen: fileData.specimen ?? false,
    options_detailed: q.options_detailed ?? null,
  });

  return {
    id: q.id,
    exam_type: examType,
    year: normalizeYear(q.year ?? fileData.year),
    paper: q.paper ?? fileData.paper ?? "",
    module: q.module ?? fileData.module ?? "",
    section,
    subject,
    part: q.part ?? "",
    question_number: q.question_number ?? 0,
    question_text: q.question_text ?? "",
    question_images: JSON.stringify(questionImages),
    options: JSON.stringify(options),
    correct_answer: q.correct_answer ?? "",
    explanation: q.explanation ?? "",
    explanation_images: JSON.stringify(explanationImages),
    screenshot: q.screenshot ?? "",
    enrichment,
    metadata,
  };
}

function loadEnrichmentMap(): Map<string, unknown> {
  const map = new Map<string, unknown>();
  for (const dir of ENRICHED_DIRS) {
    if (!fs.existsSync(dir)) continue;
    walkAndCollectEnrichment(dir, map);
  }
  return map;
}

function walkAndCollectEnrichment(dir: string, map: Map<string, unknown>) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkAndCollectEnrichment(fullPath, map);
    } else if (entry.name.endsWith(".json")) {
      const data = JSON.parse(fs.readFileSync(fullPath, "utf8")) as CorpusFile;
      for (const q of data.questions ?? []) {
        if (q.enrichment) {
          map.set(q.id, q.enrichment);
        }
      }
    }
  }
}

function findJsonFiles(dir: string): string[] {
  const results: string[] = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...findJsonFiles(fullPath));
    } else if (entry.name.endsWith(".json") && !entry.name.endsWith(".json.bak")) {
      results.push(fullPath);
    }
  }
  return results;
}

function main() {
  // Ensure data dir
  const dataDir = path.dirname(DB_PATH);
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  // Remove old DB for clean import
  if (fs.existsSync(DB_PATH)) {
    fs.unlinkSync(DB_PATH);
  }

  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");

  // Create schema. Schema is mirrored from src/lib/db.ts (initSchema) —
  // keep the two in sync. The runtime migration in db.ts handles ALTERs
  // on pre-existing DBs; this script builds a fresh DB so all columns
  // appear directly in CREATE.
  db.exec(`
    CREATE TABLE IF NOT EXISTS questions (
      id              TEXT PRIMARY KEY,
      exam_type       TEXT NOT NULL,
      year            TEXT,
      paper           TEXT,
      module          TEXT,
      section         TEXT,
      subject         TEXT,
      part            TEXT,
      question_number INTEGER NOT NULL,
      question_text   TEXT NOT NULL,
      question_images TEXT DEFAULT '[]',
      options         TEXT NOT NULL,
      correct_answer  TEXT NOT NULL,
      explanation     TEXT DEFAULT '',
      explanation_images TEXT DEFAULT '[]',
      screenshot      TEXT DEFAULT '',
      enrichment      TEXT,
      metadata        TEXT DEFAULT '{}',
      source                     TEXT NOT NULL DEFAULT 'corpus',
      generated_from_template_id TEXT,
      difficulty_score           REAL,
      created_at      TEXT DEFAULT (datetime('now')),
      updated_at      TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_questions_exam_type ON questions(exam_type);
    CREATE INDEX IF NOT EXISTS idx_questions_year ON questions(year);
    CREATE INDEX IF NOT EXISTS idx_questions_module ON questions(module);
    CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject);
    CREATE INDEX IF NOT EXISTS idx_questions_source ON questions(source);

    CREATE TABLE IF NOT EXISTS attempt_stats (
      question_id     TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
      times_answered  INTEGER DEFAULT 0,
      times_correct   INTEGER DEFAULT 0,
      avg_time_ms     REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS generation_attempts (
      id              TEXT PRIMARY KEY,
      batch_id        TEXT NOT NULL,
      spec_topic      TEXT NOT NULL,
      model           TEXT NOT NULL,
      prompt_hash     TEXT,
      question_text   TEXT NOT NULL,
      options         TEXT NOT NULL,
      correct_answer  TEXT NOT NULL,
      explanation     TEXT DEFAULT '',
      status          TEXT NOT NULL DEFAULT 'pending',
      reject_reason   TEXT,
      question_id     TEXT,
      created_at      TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_attempts_batch  ON generation_attempts(batch_id);
    CREATE INDEX IF NOT EXISTS idx_attempts_topic  ON generation_attempts(spec_topic);
    CREATE INDEX IF NOT EXISTS idx_attempts_status ON generation_attempts(status);
    CREATE INDEX IF NOT EXISTS idx_attempts_model  ON generation_attempts(model);

    CREATE TABLE IF NOT EXISTS quality_reviews (
      id              TEXT PRIMARY KEY,
      attempt_id      TEXT NOT NULL REFERENCES generation_attempts(id) ON DELETE CASCADE,
      gate            TEXT NOT NULL,
      passed          INTEGER NOT NULL,
      score           REAL,
      reason          TEXT,
      reviewer_model  TEXT,
      metadata        TEXT DEFAULT '{}',
      created_at      TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_reviews_attempt ON quality_reviews(attempt_id);
    CREATE INDEX IF NOT EXISTS idx_reviews_gate    ON quality_reviews(gate);

    CREATE TABLE IF NOT EXISTS coverage_targets (
      id              TEXT PRIMARY KEY,
      module          TEXT NOT NULL,
      topic           TEXT NOT NULL,
      difficulty      TEXT NOT NULL,
      target_pct      REAL NOT NULL,
      notes           TEXT DEFAULT '',
      updated_at      TEXT DEFAULT (datetime('now'))
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_coverage_unique
      ON coverage_targets(module, topic, difficulty);

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

  const enrichmentMap = loadEnrichmentMap();

  const insert = db.prepare(`
    INSERT INTO questions (id, exam_type, year, paper, module, section, subject, part,
                           question_number, question_text, question_images, options,
                           correct_answer, explanation, explanation_images, screenshot,
                           enrichment, metadata)
    VALUES (@id, @exam_type, @year, @paper, @module, @section, @subject, @part,
            @question_number, @question_text, @question_images, @options,
            @correct_answer, @explanation, @explanation_images, @screenshot,
            @enrichment, @metadata)
  `);

  const jsonFiles = findJsonFiles(CORPUS_DIR);
  console.log(`Found ${jsonFiles.length} JSON files in corpus`);

  let totalImported = 0;
  let totalSkipped = 0;
  const stats: Record<string, number> = {};

  const tx = db.transaction(() => {
    for (const filePath of jsonFiles) {
      const fileData = JSON.parse(fs.readFileSync(filePath, "utf8")) as CorpusFile;
      const questions = fileData.questions ?? [];

      for (const q of questions) {
        if (!q.id || !q.question_text) {
          totalSkipped++;
          continue;
        }

        // Merge enrichment if available
        if (!q.enrichment && enrichmentMap.has(q.id)) {
          (q as CorpusQuestion).enrichment = enrichmentMap.get(q.id);
        }

        const row = normalizeQuestion(fileData, q, filePath);

        try {
          insert.run(row);
          totalImported++;
          stats[row.exam_type] = (stats[row.exam_type] ?? 0) + 1;
        } catch (e) {
          console.error(`Failed to insert ${q.id}:`, e);
          totalSkipped++;
        }
      }
    }
  });

  tx();

  console.log(`\nImport complete:`);
  console.log(`  Total imported: ${totalImported}`);
  console.log(`  Skipped: ${totalSkipped}`);
  for (const [exam, count] of Object.entries(stats).sort()) {
    console.log(`    ${exam}: ${count}`);
  }

  // Verify
  const count = db.prepare("SELECT COUNT(*) as c FROM questions").get() as { c: number };
  console.log(`\nDatabase verification: ${count.c} questions in ${DB_PATH}`);

  db.close();
}

main();
