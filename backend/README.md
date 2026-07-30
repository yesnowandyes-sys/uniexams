# ESAT Gymnasium Backend

Express.js + SQLite backend for storing questions, user accounts, and answer history.

## Quick Start

```bash
cd shared/backend

# Install dependencies
npm install

# Initialize database (auto-runs on first start)
npm start

# Seed with test questions (optional)
node scripts/seed-questions.js
```

## API Endpoints

### Health
- `GET /api/health` — Server health check

### Users
- `POST /api/users` — Create a new user
  - Body: `{ name, email? }`
  - Returns: `{ id, name, email, created_at }`
- `GET /api/users/:id` — Get user by ID
- `DELETE /api/users/:id` — Delete user and all attempts
- `GET /api/users/:id/attempts` — Get all attempts for a user
- `GET /api/users/:id/stats` — Get user statistics (accuracy, avg time, per-module stats)

### Questions
- `GET /api/questions` — List all questions
  - Query params: `?module=maths1&difficulty=Medium&limit=10`
- `GET /api/questions/:id` — Get question by ID (without answer)
- `POST /api/questions` — Create a new question
  - Body: `{ id, module, question_text, options, correct_answer, ... }`
- `DELETE /api/questions/:id` — Delete a question

### Attempts
- `POST /api/attempts` — Record a user's attempt
  - Body: `{ user_id, question_id, selected_answer, time_taken_ms }`
  - Returns: `{ id, is_correct, correct_answer }`

## Database Schema

### users
- `id` (TEXT, PRIMARY KEY)
- `name` (TEXT, NOT NULL)
- `email` (TEXT, UNIQUE, nullable)
- `created_at` (TEXT, timestamp)

### questions
- `id` (TEXT, PRIMARY KEY)
- `exam_type`, `year`, `paper`, `module`, `section`, `subject`, `part`
- `question_number`, `question_text`, `question_images` (JSON)
- `options` (JSON), `correct_answer`, `explanation`, `explanation_images` (JSON)
- `difficulty`, `source` (default: 'generated')
- `created_at` (timestamp)

### user_attempts
- `id` (TEXT, PRIMARY KEY)
- `user_id` (FK → users.id)
- `question_id` (FK → questions.id)
- `selected_answer` (TEXT, NOT NULL)
- `is_correct` (INTEGER, 0/1)
- `time_taken_ms` (INTEGER, NOT NULL)
- `attempted_at` (timestamp)
- `UNIQUE(user_id, question_id)` — only one attempt per question

## Usage Examples

### Create a user
```bash
curl -X POST http://localhost:3001/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'
```

### List questions
```bash
curl http://localhost:3001/api/questions?module=maths1&limit=5
```

### Submit an attempt
```bash
curl -X POST http://localhost:3001/api/attempts \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "question_id": "gen_q1",
    "selected_answer": "B",
    "time_taken_ms": 45000
  }'
```

### Get user stats
```bash
curl http://localhost:3001/api/users/user-123/stats
```

## Why This Approach

- **Simple**: Single-file SQLite, no external dependencies
- **Fast**: In-memory queries, WAL mode for concurrency
- **Portable**: Database file can be copied/migrated to Postgres later
- **Testable**: Full REST API for testing UX before website build
- **Migratable**: Schema mirrors the production `shared/src/lib/db.ts` structure

## Next Steps

1. Run the server: `npm start`
2. Seed test questions: `node scripts/seed-questions.js`
3. Test the API with curl/Postman
4. Build frontend to consume this API
5. Migrate to production database (Postgres) when ready