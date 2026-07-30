/**
 * Idempotent enrichment-only updater.
 *
 * Scans all enriched-output/ subdirectories for question enrichment payloads
 * and updates the `enrichment` column for matching question IDs in the SQLite
 * database. Does NOT touch any other question fields, so it is safe to run
 * repeatedly while the opus-batch enrichment job is still producing output.
 *
 * Usage:
 *   npx tsx scripts/update-enrichment.ts
 */
import Database from "better-sqlite3";
import fs from "fs";
import path from "path";

const ENRICHED_DIRS = [
  path.join(process.cwd(), "enriched-output", "opus-batch"),
  path.join(process.cwd(), "enriched-output", "opus-trial"),
  path.join(process.cwd(), "enriched-output", "glm-trial-v2"),
  path.join(process.cwd(), "enriched-output", "glm-trial"),
];
const DB_PATH = path.join(process.cwd(), "data", "questions.db");

interface EnrichmentPayload {
  status?: string;
  model?: string;
  enriched_at?: string;
  markdown?: string;
  difficulty_rating?: number;
  difficulty_category?: string;
  topic_classification?: {
    module?: string;
    module_code?: string;
    topic_code?: string;
    topic_name?: string;
    content_code?: string;
    question_type?: string;
    is_out_of_spec?: boolean;
  };
  ocr_corrections?: unknown;
  error?: string;
}

interface CorpusFile {
  questions?: Array<{ id: string; enrichment?: EnrichmentPayload }>;
}

function walkAndCollectEnrichment(
  dir: string,
  map: Map<string, EnrichmentPayload>
): void {
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    if (entry.name.startsWith("_")) continue; // skip state/log files
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkAndCollectEnrichment(fullPath, map);
    } else if (entry.name.endsWith(".json")) {
      let data: CorpusFile;
      try {
        data = JSON.parse(fs.readFileSync(fullPath, "utf8")) as CorpusFile;
      } catch (e) {
        console.warn(`Skipping malformed ${fullPath}: ${(e as Error).message}`);
        continue;
      }
      for (const q of data.questions ?? []) {
        if (q.id && q.enrichment) {
          // Last-writer-wins: later dirs override earlier ones.
          // Iterate ENRICHED_DIRS in priority order (opus-batch first).
          if (!map.has(q.id)) {
            map.set(q.id, q.enrichment);
          }
        }
      }
    }
  }
}

function main(): void {
  if (!fs.existsSync(DB_PATH)) {
    console.error(`Database not found at ${DB_PATH}. Run import-corpus first.`);
    process.exit(1);
  }

  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");

  const enrichmentMap = new Map<string, EnrichmentPayload>();
  for (const dir of ENRICHED_DIRS) {
    if (!fs.existsSync(dir)) continue;
    walkAndCollectEnrichment(dir, enrichmentMap);
  }
  console.log(`Loaded enrichment payloads for ${enrichmentMap.size} questions`);

  const existing = db
    .prepare("SELECT id, enrichment IS NOT NULL AS has_enrichment FROM questions")
    .all() as Array<{ id: string; has_enrichment: number }>;
  const existingIds = new Set(existing.map((r) => r.id));
  console.log(`Database currently has ${existing.length} questions`);

  const update = db.prepare(
    "UPDATE questions SET enrichment = ?, updated_at = datetime('now') WHERE id = ?"
  );

  let updated = 0;
  let skipped = 0;
  let notInDb = 0;
  const statsByStatus: Record<string, number> = {};
  const statsByDifficulty: Record<string, number> = {};

  const tx = db.transaction(() => {
    for (const [id, enrichment] of enrichmentMap.entries()) {
      if (!existingIds.has(id)) {
        notInDb++;
        continue;
      }
      const status = enrichment.status ?? "unknown";
      // Only persist useful enrichment: success or out_of_spec classifications.
      // Skip empty/error payloads so we don't clobber good data with failures.
      if (status === "error" || (!enrichment.markdown && !enrichment.topic_classification)) {
        skipped++;
        continue;
      }
      update.run(JSON.stringify(enrichment), id);
      updated++;
      statsByStatus[status] = (statsByStatus[status] ?? 0) + 1;
      const diff = enrichment.difficulty_category ?? "unknown";
      statsByDifficulty[diff] = (statsByDifficulty[diff] ?? 0) + 1;
    }
  });
  tx();

  console.log(`\nUpdate complete:`);
  console.log(`  Enrichment payloads applied: ${updated}`);
  console.log(`  Skipped (empty/error): ${skipped}`);
  console.log(`  Not in DB (orphan): ${notInDb}`);
  console.log(`\nBy status:`);
  for (const [s, n] of Object.entries(statsByStatus).sort()) {
    console.log(`  ${s}: ${n}`);
  }
  console.log(`\nBy difficulty:`);
  for (const [d, n] of Object.entries(statsByDifficulty).sort()) {
    console.log(`  ${d}: ${n}`);
  }

  const totalEnriched = db
    .prepare("SELECT COUNT(*) AS c FROM questions WHERE enrichment IS NOT NULL")
    .get() as { c: number };
  console.log(
    `\nDatabase now has ${totalEnriched.c}/${existing.length} questions with enrichment`
  );

  db.close();
}

main();
