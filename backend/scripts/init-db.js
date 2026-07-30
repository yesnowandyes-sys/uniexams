/**
 * Initialize the database with schema
 */

import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const DB_PATH = path.join(process.cwd(), 'data', 'esat_backend.db');

// Ensure data directory exists
const dir = path.dirname(DB_PATH);
if (!fs.existsSync(dir)) {
  fs.mkdirSync(dir, { recursive: true });
}

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

console.log('🔧 Initializing database schema...');

// Users table
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
  );
`);

// Questions table
db.exec(`
  CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    exam_type TEXT NOT NULL,
    year TEXT,
    paper TEXT,
    module TEXT NOT NULL,
    section TEXT,
    subject TEXT,
    part TEXT,
    question_number INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_images TEXT DEFAULT '[]',
    options TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT DEFAULT '',
    explanation_images TEXT DEFAULT '[]',
    difficulty TEXT,
    source TEXT NOT NULL DEFAULT 'generated',
    created_at TEXT DEFAULT (datetime('now'))
  );
`);

// User attempts table
db.exec(`
  CREATE TABLE IF NOT EXISTS user_attempts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    selected_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    time_taken_ms INTEGER NOT NULL,
    attempted_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, question_id)
  );
`);

// Indexes
db.exec(`
  CREATE INDEX IF NOT EXISTS idx_user_attempts_user ON user_attempts(user_id);
  CREATE INDEX IF NOT EXISTS idx_user_attempts_question ON user_attempts(question_id);
  CREATE INDEX IF NOT EXISTS idx_questions_module ON questions(module);
  CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);
`);

console.log('✅ Database schema initialized');
console.log(`📦 Database location: ${DB_PATH}`);

// Show table info
console.log('\n📋 Tables:');
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
tables.forEach(t => console.log(`  - ${t.name}`));

db.close();