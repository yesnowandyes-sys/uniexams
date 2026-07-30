#!/usr/bin/env bash
# Cron wrapper for GLM-5.2 question generation.
# Runs the script, captures output, appends a summary line for easy parsing.

set -euo pipefail

LOGFILE="/home/ubuntu/.paperclip/esat-shared/data/generation-cron.log"
DB="/home/ubuntu/.paperclip/esat-shared/data/questions.db"
SCRIPT="/home/ubuntu/.paperclip/esat-shared/scripts/generate_and_verify_glm.py"

echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') START ===" >> "$LOGFILE"

cd /home/ubuntu/.paperclip/esat-shared && \
  python3 "$SCRIPT" --no-wait --max-runtime 17940 >> "$LOGFILE" 2>&1
EXIT_CODE=$?

echo "EXIT_CODE=$EXIT_CODE" >> "$LOGFILE"
echo "DB_TOTAL=$(sqlite3 "$DB" 'SELECT COUNT(*) FROM questions;')" >> "$LOGFILE"
echo "DB_GENERATED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM questions WHERE source='generated';")" >> "$LOGFILE"
echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') END ===" >> "$LOGFILE"
