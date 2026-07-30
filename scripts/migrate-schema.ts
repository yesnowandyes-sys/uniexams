/**
 * Standalone runner for the schema migration defined in src/lib/db.ts.
 * Used to verify the migration against an existing database without
 * going through the Next.js dev server. Idempotent — safe to re-run.
 *
 * Usage:
 *   npx tsx scripts/migrate-schema.ts
 */
import { getDb } from "../src/lib/db";

const db = getDb();

// Verify presence of the new columns on `questions`.
const cols = db.prepare("PRAGMA table_info(questions)").all() as Array<{ name: string }>;
const colNames = cols.map((c) => c.name);
console.log("questions columns:", colNames.join(", "));

for (const required of ["source", "generated_from_template_id", "difficulty_score"]) {
  if (!colNames.includes(required)) {
    console.error(`MISSING column: ${required}`);
    process.exit(1);
  }
}

// Backfill verification: every corpus row should have source='corpus'.
const nullCount = db
  .prepare("SELECT COUNT(*) AS c FROM questions WHERE source IS NULL")
  .get() as { c: number };
console.log(`rows with NULL source (should be 0): ${nullCount.c}`);

const sourceBreakdown = db
  .prepare("SELECT source, COUNT(*) AS c FROM questions GROUP BY source")
  .all() as Array<{ source: string; c: number }>;
console.log("source breakdown:", sourceBreakdown);

// Verify the four new tables exist.
const tables = db
  .prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
  .all() as Array<{ name: string }>;
const tableNames = tables.map((t) => t.name);
console.log("tables:", tableNames.join(", "));

for (const required of [
  "generation_attempts",
  "quality_reviews",
  "coverage_targets",
  "pattern_files",
]) {
  if (!tableNames.includes(required)) {
    console.error(`MISSING table: ${required}`);
    process.exit(1);
  }
}

// Re-run getDb() to confirm idempotency (initSchema runs again internally).
getDb();
console.log("re-invocation succeeded — migration is idempotent");

console.log("\nMigration OK.");
