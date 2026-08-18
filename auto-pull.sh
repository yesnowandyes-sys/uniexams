#!/bin/bash
# Auto-pull uniexams repo from GitHub every 60 seconds
REPO_DIR="/home/ubuntu/uniexams"
LOCK_FILE="/tmp/uniexams-pull.lock"
LOG_FILE="/home/ubuntu/uniexams/pull.log"

exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

cd "$REPO_DIR" || exit 1

BEFORE=$(git rev-parse HEAD)
git pull --ff-only --quiet 2>&1 >> "$LOG_FILE"
AFTER=$(git rev-parse HEAD)

if [ "$BEFORE" != "$AFTER" ]; then
    echo "$(date -Iseconds) Pulled $(git log --oneline -1)" >> "$LOG_FILE"
fi
