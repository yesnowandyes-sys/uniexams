#!/bin/bash
# ensure-shared-symlinks.sh
# Ensures all Paperclip agent workspaces have a symlink to the shared ESAT project filebase.
# Run manually after hiring new agents, or set up as a cron job for automatic provisioning.

SHARED_DIR="/home/ubuntu/.paperclip/esat-shared"
WORKSPACES_DIR="/home/ubuntu/.paperclip/instances/default/workspaces"
FIX_MODE="${1:---check}"  # --check (default) or --fix

if [ ! -d "$SHARED_DIR" ]; then
  echo "ERROR: Shared directory not found at $SHARED_DIR"
  exit 1
fi

count_fixed=0
count_missing=0
count_ok=0

for ws in "$WORKSPACES_DIR"/*/; do
  [ -d "$ws" ] || continue
  name=$(basename "$ws")
  link="$ws/shared"

  if [ -L "$link" ]; then
    target=$(readlink "$link")
    if [ "$target" = "$SHARED_DIR/" ] || [ "$target" = "$SHARED_DIR" ]; then
      echo "OK $name"
      count_ok=$((count_ok + 1))
    else
      echo "WARN $name -> $target (wrong target, should be $SHARED_DIR)"
      count_missing=$((count_missing + 1))
      if [ "$FIX_MODE" = "--fix" ]; then
        rm "$link"
        ln -s "$SHARED_DIR" "$link"
        echo "   -> Fixed: $name -> $SHARED_DIR"
        count_fixed=$((count_fixed + 1))
      fi
    fi
  elif [ -e "$link" ]; then
    echo "WARN $name (shared exists but is not a symlink)"
    count_missing=$((count_missing + 1))
  else
    echo "MISSING $name (no shared symlink)"
    count_missing=$((count_missing + 1))
    if [ "$FIX_MODE" = "--fix" ]; then
      ln -s "$SHARED_DIR" "$link"
      echo "   -> Created: $name -> $SHARED_DIR"
      if [ ! -f "$ws/CLAUDE.md" ]; then
        cat > "$ws/CLAUDE.md" << 'CLAUDEEOF'
# Project Files

Project files live in the `shared/` directory (symlinked from `/home/ubuntu/.paperclip/esat-shared/`).

Start by reading any README or context files in `shared/` for an overview of the project.
CLAUDEEOF
        echo "   -> Created: $name/CLAUDE.md"
      fi
      count_fixed=$((count_fixed + 1))
    fi
  fi
done

# Also check project managed folders (where Claude Code/OpenCode agents actually work)
PROJECTS_DIR="/home/ubuntu/.paperclip/instances/default/projects"

if [ -d "$PROJECTS_DIR" ]; then
  for proj_co in "$PROJECTS_DIR"/*/; do
    [ -d "$proj_co" ] || continue
    for proj in "$proj_co"/*/; do
      [ -d "$proj" ] || continue
      managed="$proj/_default"
      if [ ! -d "$managed" ]; then
        continue
      fi
      name=$(basename "$proj")
      link="$managed/shared"

      if [ -L "$link" ]; then
        target=$(readlink "$link")
        if [ "$target" = "$SHARED_DIR/" ] || [ "$target" = "$SHARED_DIR" ]; then
          echo "OK managed/$name"
          count_ok=$((count_ok + 1))
        else
          echo "WARN managed/$name -> $target (wrong target)"
          count_missing=$((count_missing + 1))
          if [ "$FIX_MODE" = "--fix" ]; then
            rm "$link"; ln -s "$SHARED_DIR" "$link"
            echo "   -> Fixed: managed/$name -> $SHARED_DIR"
            count_fixed=$((count_fixed + 1))
          fi
        fi
      elif [ -e "$link" ]; then
        echo "WARN managed/$name (shared exists but is not a symlink)"
      else
        echo "MISSING managed/$name (no shared symlink)"
        count_missing=$((count_missing + 1))
        if [ "$FIX_MODE" = "--fix" ]; then
          ln -s "$SHARED_DIR" "$link"
          if [ ! -f "$managed/CLAUDE.md" ]; then
            cat > "$managed/CLAUDE.md" << 'CLAUDEEOF'
# Project Files

Project files live in the `shared/` directory (symlinked from `/home/ubuntu/.paperclip/esat-shared/`).

Start by reading any README or context files in `shared/` for an overview of the project.
CLAUDEEOF
            echo "   -> Created: managed/$name/CLAUDE.md"
          fi
          echo "   -> Created: managed/$name -> $SHARED_DIR"
          count_fixed=$((count_fixed + 1))
        fi
      fi
    done
  done
fi

echo ""
echo "Summary: $count_ok ok, $count_missing missing, $count_fixed fixed"
[ $count_missing -gt 0 ] && [ "$FIX_MODE" != "--fix" ] && echo "Run with --fix to create missing symlinks."
