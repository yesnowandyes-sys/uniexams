/**
 * ESAT Gymnasium Backend API
 *
 * Express.js server with SQLite database for:
 * - Questions storage
 * - User accounts
 * - Answer history (time taken, answer choice)
 */

import express from 'express';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const app = express();
const PORT = process.env.PORT || 3001;
const DB_PATH = path.join(process.cwd(), 'data', 'esat_backend.db');

// Middleware
app.use(cors());
app.use(express.json());

// Database initialization
function initDb() {
  const db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  // Users table
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      email TEXT UNIQUE,
      created_at TEXT DEFAULT (datetime('now'))
    );
  `);

  // Questions table (mirrors the schema from shared/src/lib/db.ts)
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

  // User attempts table (answer history)
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

  // Indexes for performance
  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_user_attempts_user ON user_attempts(user_id);
    CREATE INDEX IF NOT EXISTS idx_user_attempts_question ON user_attempts(question_id);
    CREATE INDEX IF NOT EXISTS idx_questions_module ON questions(module);
    CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);
  `);

  return db;
}

const db = initDb();

// Routes

/**
 * GET /api/health
 * Health check endpoint
 */
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

/**
 * POST /api/users
 * Create a new user
 */
app.post('/api/users', (req, res) => {
  const { name, email } = req.body;

  if (!name) {
    return res.status(400).json({ error: 'name is required' });
  }

  try {
    const id = uuidv4();
    db.prepare(
      'INSERT INTO users (id, name, email) VALUES (?, ?, ?)'
    ).run(id, name, email || null);

    const user = db.prepare('SELECT id, name, email, created_at FROM users WHERE id = ?').get(id);
    res.status(201).json(user);
  } catch (error) {
    if (error.message.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'email already exists' });
    }
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/users/:id
 * Get user by ID
 */
app.get('/api/users/:id', (req, res) => {
  const { id } = req.params;
  const user = db.prepare(
    'SELECT id, name, email, created_at FROM users WHERE id = ?'
  ).get(id);

  if (!user) {
    return res.status(404).json({ error: 'user not found' });
  }

  res.json(user);
});

/**
 * GET /api/questions
 * List all questions with optional filters
 */
app.get('/api/questions', (req, res) => {
  const { module, difficulty, limit } = req.query;

  let query = 'SELECT * FROM questions';
  const params = [];

  const conditions = [];
  if (module) {
    conditions.push('module = ?');
    params.push(module);
  }
  if (difficulty) {
    conditions.push('difficulty = ?');
    params.push(difficulty);
  }

  if (conditions.length > 0) {
    query += ' WHERE ' + conditions.join(' AND ');
  }

  query += ' ORDER BY created_at DESC';

  if (limit) {
    query += ' LIMIT ?';
    params.push(parseInt(limit));
  }

  const questions = db.prepare(query).all(...params);
  res.json(questions);
});

/**
 * GET /api/questions/:id
 * Get question by ID (without answer)
 */
app.get('/api/questions/:id', (req, res) => {
  const { id } = req.params;

  const question = db.prepare(
    `SELECT id, exam_type, year, paper, module, section, subject, part,
            question_number, question_text, question_images, options,
            explanation, explanation_images, difficulty, created_at
     FROM questions WHERE id = ?`
  ).get(id);

  if (!question) {
    return res.status(404).json({ error: 'question not found' });
  }

  // Parse JSON fields
  question.options = JSON.parse(question.options);
  question.question_images = JSON.parse(question.question_images);
  question.explanation_images = JSON.parse(question.explanation_images);

  res.json(question);
});

/**
 * POST /api/questions
 * Create a new question
 */
app.post('/api/questions', (req, res) => {
  const {
    id,
    exam_type,
    year,
    paper,
    module,
    section,
    subject,
    part,
    question_number,
    question_text,
    question_images,
    options,
    correct_answer,
    explanation,
    explanation_images,
    difficulty,
  } = req.body;

  if (!id || !exam_type || !module || !question_text || !options || !correct_answer) {
    return res.status(400).json({ error: 'missing required fields' });
  }

  try {
    db.prepare(`
      INSERT INTO questions (
        id, exam_type, year, paper, module, section, subject, part,
        question_number, question_text, question_images, options,
        correct_answer, explanation, explanation_images, difficulty
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      exam_type,
      year || null,
      paper || null,
      module,
      section || null,
      subject || null,
      part || null,
      question_number,
      question_text,
      JSON.stringify(question_images || []),
      JSON.stringify(options),
      correct_answer,
      explanation || '',
      JSON.stringify(explanation_images || []),
      difficulty || null
    );

    res.status(201).json({ id, created: true });
  } catch (error) {
    if (error.message.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'question already exists' });
    }
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/attempts
 * Record a user's attempt at a question
 */
app.post('/api/attempts', (req, res) => {
  const { user_id, question_id, selected_answer, time_taken_ms } = req.body;

  if (!user_id || !question_id || !selected_answer) {
    return res.status(400).json({ error: 'user_id, question_id, and selected_answer are required' });
  }

  if (typeof time_taken_ms !== 'number' || time_taken_ms < 0) {
    return res.status(400).json({ error: 'time_taken_ms must be a non-negative number' });
  }

  try {
    // Get correct answer
    const question = db.prepare(
      'SELECT correct_answer FROM questions WHERE id = ?'
    ).get(question_id);

    if (!question) {
      return res.status(404).json({ error: 'question not found' });
    }

    const is_correct = question.correct_answer === selected_answer ? 1 : 0;

    // Upsert attempt (replace if exists)
    const id = uuidv4();
    db.prepare(`
      INSERT INTO user_attempts (id, user_id, question_id, selected_answer, is_correct, time_taken_ms)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(user_id, question_id) DO UPDATE SET
        selected_answer = excluded.selected_answer,
        is_correct = excluded.is_correct,
        time_taken_ms = excluded.time_taken_ms,
        attempted_at = datetime('now')
    `).run(id, user_id, question_id, selected_answer, is_correct, time_taken_ms);

    res.status(201).json({
      id,
      is_correct: Boolean(is_correct),
      correct_answer: question.correct_answer,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/users/:id/attempts
 * Get all attempts for a user
 */
app.get('/api/users/:id/attempts', (req, res) => {
  const { id } = req.params;

  const attempts = db.prepare(`
    SELECT
      ua.id,
      ua.question_id,
      q.question_text,
      q.module,
      q.difficulty,
      ua.selected_answer,
      q.correct_answer,
      ua.is_correct,
      ua.time_taken_ms,
      ua.attempted_at
    FROM user_attempts ua
    JOIN questions q ON ua.question_id = q.id
    WHERE ua.user_id = ?
    ORDER BY ua.attempted_at DESC
  `).all(id);

  res.json(attempts);
});

/**
 * GET /api/users/:id/stats
 * Get statistics for a user
 */
app.get('/api/users/:id/stats', (req, res) => {
  const { id } = req.params;

  const stats = db.prepare(`
    SELECT
      COUNT(*) as total_attempts,
      SUM(is_correct) as correct_attempts,
      AVG(time_taken_ms) as avg_time_ms,
      MIN(time_taken_ms) as min_time_ms,
      MAX(time_taken_ms) as max_time_ms
    FROM user_attempts
    WHERE user_id = ?
  `).get(id);

  // Stats per module
  const module_stats = db.prepare(`
    SELECT
      q.module,
      COUNT(*) as attempts,
      SUM(is_correct) as correct,
      AVG(time_taken_ms) as avg_time_ms
    FROM user_attempts ua
    JOIN questions q ON ua.question_id = q.id
    WHERE ua.user_id = ?
    GROUP BY q.module
    ORDER BY q.module
  `).all(id);

  res.json({
    ...stats,
    module_stats,
    accuracy: stats.total_attempts > 0
      ? Math.round((stats.correct_attempts / stats.total_attempts) * 100)
      : 0,
  });
});

/**
 * DELETE /api/users/:id
 * Delete a user and all their attempts
 */
app.delete('/api/users/:id', (req, res) => {
  const { id } = req.params;

  const result = db.prepare('DELETE FROM users WHERE id = ?').run(id);

  if (result.changes === 0) {
    return res.status(404).json({ error: 'user not found' });
  }

  res.json({ deleted: true });
});

/**
 * DELETE /api/questions/:id
 * Delete a question
 */
app.delete('/api/questions/:id', (req, res) => {
  const { id } = req.params;

  const result = db.prepare('DELETE FROM questions WHERE id = ?').run(id);

  if (result.changes === 0) {
    return res.status(404).json({ error: 'question not found' });
  }

  res.json({ deleted: true });
});

// Start server
app.listen(PORT, () => {
  console.log(`ESAT Backend API running on http://localhost:${PORT}`);
  console.log(`Database: ${DB_PATH}`);
  console.log(`\nAvailable endpoints:`);
  console.log(`  GET  /api/health`);
  console.log(`  POST /api/users`);
  console.log(`  GET  /api/users/:id`);
  console.log(`  GET  /api/users/:id/attempts`);
  console.log(`  GET  /api/users/:id/stats`);
  console.log(`  DELETE /api/users/:id`);
  console.log(`  GET  /api/questions`);
  console.log(`  GET  /api/questions/:id`);
  console.log(`  POST /api/questions`);
  console.log(`  DELETE /api/questions/:id`);
  console.log(`  POST /api/attempts`);
});