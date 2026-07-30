/**
 * Seed the database with test questions from /tmp/q*.json
 */

import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const DB_PATH = path.join(process.cwd(), 'data', 'esat_backend.db');
const QUESTIONS_DIR = '/tmp';

const db = new Database(DB_PATH);
db.pragma('foreign_keys = ON');

console.log('📚 Seeding database with generated questions...');

// Only use the valid questions we verified
const validQuestions = ['q1.json', 'q5.json', 'q6.json', 'q10.json'];

console.log(`Processing ${validQuestions.length} valid question files`);

let imported = 0;
let skipped = 0;

for (const file of validQuestions) {
  const filePath = path.join(QUESTIONS_DIR, file);

  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const data = JSON.parse(content);

    if (!data.question) {
      console.log(`⏭️  Skipping ${file}: no 'question' field`);
      skipped++;
      continue;
    }

    const q = data.question;
    const id = q.id || `gen_${file.replace('.json', '')}`;

    // Map spec codes to modules
    const specToModule = {
      'MATHS1.M1': 'maths1',
      'PHYS.P3': 'physics',
      'CHEM.C2': 'chemistry',
      'MATHS2.M3': 'maths2',
      'PHYS.P1': 'physics',
      'PHYS.P5': 'physics',
      'CHEM.C4': 'chemistry',
      'BIO.B2': 'biology',
    };

    const module = specToModule[q.spec_topic] || 'maths1';

    db.prepare(`
      INSERT OR REPLACE INTO questions (
        id, exam_type, year, paper, module, section, subject, part,
        question_number, question_text, question_images, options,
        correct_answer, explanation, explanation_images, difficulty, source
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      'esat',
      '2024',
      'generated',
      module,
      null,
      null,
      null,
      1,
      q.question_text,
      JSON.stringify(q.question_images || []),
      JSON.stringify(q.options || {}),
      q.correct_answer,
      q.explanation || '',
      JSON.stringify(q.explanation_images || []),
      q.difficulty || 'Medium',
      'generated'
    );

    imported++;
    console.log(`✅ Imported: ${id} (${module} - ${q.difficulty})`);
  } catch (error) {
    console.log(`❌ Failed to import ${file}: ${error.message}`);
    skipped++;
  }
}

console.log(`\n📊 Import complete:`);
console.log(`   ✅ Imported: ${imported}`);
console.log(`   ⏭️  Skipped: ${skipped}`);

// Show stats
const count = db.prepare('SELECT COUNT(*) as count FROM questions').get();
console.log(`   📦 Total questions in DB: ${count.count}`);

db.close();