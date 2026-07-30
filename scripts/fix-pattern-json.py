#!/usr/bin/env python3
"""
Re-parse pattern artefacts with a tolerant JSON repair pass.

GLM-5.2 (the gateway-mapped "claude-opus-4-8" / "claude-haiku-4-5" model
on the z.ai gateway) frequently emits single-backslash LaTeX commands
inside JSON strings (e.g. "\\propto", "\\theta", "\\frac") which is invalid
JSON. This script reads the `_raw` field the extractor preserved, repairs
those escapes, parses, and rewrites the catalogue files in place.

Idempotent: re-running on already-parsed files is a no-op.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PATTERNS_DIR = Path(__file__).resolve().parent.parent / "patterns"

# Known JSON escape sequences (keep these as-is).
# Anything else after a single backslash is invalid JSON; double it.
VALID_JSON_ESCAPES = {'"', "\\", "/", "b", "f", "n", "r", "t", "u"}


def repair_json_string(s: str) -> str:
    """Double every backslash that doesn't precede a valid JSON escape char."""
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in VALID_JSON_ESCAPES:
                out.append(ch)
                out.append(nxt)
                i += 2
                continue
            # Invalid escape: double the backslash
            out.append("\\")
            out.append("\\")
            # Keep the next char to be processed normally
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def tolerant_parse_array(raw: str) -> list | None:
    """Try strict JSON first, then a repair pass on the array slice."""
    raw = raw.strip()
    # Strip code fences if present
    raw = re.sub(r"^```[a-zA-Z]*\s*\n", "", raw)
    raw = re.sub(r"\n```\s*$", "", raw)
    i, j = raw.find("["), raw.rfind("]")
    if i < 0 or j < 0 or j < i:
        return None
    candidate = raw[i : j + 1]
    # Attempt 1: strict
    try:
        v = json.loads(candidate)
        return v if isinstance(v, list) else None
    except json.JSONDecodeError:
        pass
    # Attempt 2: repair escapes inside the slice and retry
    repaired = repair_json_string(candidate)
    try:
        v = json.loads(repaired)
        return v if isinstance(v, list) else None
    except json.JSONDecodeError as e:
        # Attempt 3: line-by-line salvage — keep objects that parse individually
        objs = []
        # Naive split on top-level object boundaries: `{ ... }` between commas
        # Use a depth tracker.
        depth = 0
        start = None
        in_str = False
        esc = False
        for k, c in enumerate(repaired):
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                if depth == 0:
                    start = k
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    obj_str = repaired[start : k + 1]
                    try:
                        objs.append(json.loads(obj_str))
                    except json.JSONDecodeError:
                        # Try repairing just this object
                        try:
                            objs.append(json.loads(repair_json_string(obj_str)))
                        except json.JSONDecodeError:
                            pass
                start = None
        return objs if objs else None


def fix_one_dir(d: Path) -> dict:
    tk = d.name
    summary = {"topic": tk, "fixed_distractors": False, "fixed_scenarios": False,
               "distractor_count": 0, "scenario_count": 0}
    # Distractor catalogue
    dpath = d / f"distractor_catalogue.{tk}.json"
    if dpath.exists():
        data = json.load(open(dpath))
        if not data.get("distractors") and data.get("_raw"):
            parsed = tolerant_parse_array(data["_raw"])
            if parsed is not None:
                data["distractors"] = parsed
                data.pop("_raw", None)
                data["parse_repaired"] = True
                dpath.write_text(json.dumps(data, indent=2))
                summary["fixed_distractors"] = True
                summary["distractor_count"] = len(parsed)
        elif data.get("distractors"):
            summary["distractor_count"] = len(data["distractors"])
    # Scenarios
    spath = d / f"insight_scenarios.{tk}.json"
    if spath.exists():
        data = json.load(open(spath))
        if not data.get("scenarios") and data.get("_raw"):
            parsed = tolerant_parse_array(data["_raw"])
            if parsed is not None:
                data["scenarios"] = parsed
                data.pop("_raw", None)
                data["parse_repaired"] = True
                spath.write_text(json.dumps(data, indent=2))
                summary["fixed_scenarios"] = True
                summary["scenario_count"] = len(parsed)
        elif data.get("scenarios"):
            summary["scenario_count"] = len(data["scenarios"])
    return summary


def main():
    if not PATTERNS_DIR.exists():
        print(f"No patterns dir at {PATTERNS_DIR}", file=sys.stderr)
        sys.exit(1)
    total_d = 0
    total_s = 0
    fixed_d = 0
    fixed_s = 0
    rows = []
    for d in sorted(PATTERNS_DIR.iterdir()):
        if not d.is_dir() or d.name == "_state":
            continue
        s = fix_one_dir(d)
        rows.append(s)
        if s["fixed_distractors"]:
            fixed_d += 1
        if s["fixed_scenarios"]:
            fixed_s += 1
        total_d += s["distractor_count"]
        total_s += s["scenario_count"]
    print(f"Topics processed: {len(rows)}")
    print(f"Repaired distractor catalogues: {fixed_d}")
    print(f"Repaired scenario files:       {fixed_s}")
    print(f"Total distractors after repair: {total_d}")
    print(f"Total scenarios after repair:   {total_s}")
    # Show a few low-count topics for spot-check
    rows.sort(key=lambda r: r["distractor_count"])
    print("\nLowest 5 distractor counts:")
    for r in rows[:5]:
        print(f"  {r['topic']}: {r['distractor_count']} distractors, {r['scenario_count']} scenarios")


if __name__ == "__main__":
    main()
