"""ESAT taxonomy loading and lookup utilities.

The taxonomy file lives at the repo root (NOT under data/):
    /home/ubuntu/.paperclip/esat-shared/esat_taxonomy.json

Structure:
    modules: [{code: "M1", name: "Mathematics 1", topics: [
        {spec_code: "M1", name: "Units", subtopics: [
            {spec_code: "M1.1", name: "...", skills: [...]}, ...
        ]}, ...
    ]}, ...]

Top-level module codes: M1, M2, P, C, B
Topic-level codes (what enrichment calls "module_code" / "topic_code"):
    M1-M7 (under module M1), MM1-MM8 (under module M2),
    P1-P7 (under P), B1-B11 (under B), C1-C17 (under C)
Finest-grain codes (spec_code on subtopics, matches enrichment "content_code"):
    e.g. M2.7, P1.2, MM1.3, B2.1, C4.6
"""

import json
import re
from functools import lru_cache
from pathlib import Path

TAXONOMY_PATH = Path("/home/ubuntu/.paperclip/esat-shared/esat_taxonomy.json")

# Topic-level code -> topic_key prefix (Appendix C of the proposal)
TOPIC_KEY_PREFIXES = {}
for i in range(1, 8):
    TOPIC_KEY_PREFIXES[f"M{i}"] = "MATHS1"
for i in range(1, 9):
    TOPIC_KEY_PREFIXES[f"MM{i}"] = "MATHS2"
for i in range(1, 8):
    TOPIC_KEY_PREFIXES[f"P{i}"] = "PHYS"
for i in range(1, 12):
    TOPIC_KEY_PREFIXES[f"B{i}"] = "BIO"
for i in range(1, 18):
    TOPIC_KEY_PREFIXES[f"C{i}"] = "CHEM"

TOPIC_CODE_RE = re.compile(r"^(MM[1-8]|M[1-7]|P[1-7]|B(1[01]|[1-9])|C(1[0-7]|[1-9]))$")
SPEC_CODE_RE = re.compile(r"^(MM[1-8]|M[1-7]|P[1-7]|B(1[01]|[1-9])|C(1[0-7]|[1-9]))\.\d+$")
MODULE_CODE_RE = re.compile(r"^(M1|M2|P|C|B)$")


@lru_cache(maxsize=1)
def load_taxonomy() -> dict:
    with open(TAXONOMY_PATH) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def valid_spec_codes() -> frozenset[str]:
    """All finest-grain spec_codes (e.g. 'M2.7', 'P1.2') — used for skills_json validation."""
    tax = load_taxonomy()
    codes = set()
    for m in tax["modules"]:
        for t in m.get("topics", []):
            for st in t.get("subtopics", []):
                codes.add(st["spec_code"])
    return frozenset(codes)


@lru_cache(maxsize=1)
def valid_topic_codes() -> frozenset[str]:
    """All topic-level codes (e.g. 'M2', 'MM1', 'P3', 'B4', 'C4')."""
    tax = load_taxonomy()
    codes = set()
    for m in tax["modules"]:
        for t in m.get("topics", []):
            codes.add(t["spec_code"])
    return frozenset(codes)


def is_valid_spec_code(code: str) -> bool:
    return code in valid_spec_codes()


def is_valid_topic_code(code: str) -> bool:
    return code in valid_topic_codes()


def clean_code_token(raw: str) -> str:
    """Strip parenthetical/explanatory text from a single code token."""
    if not raw:
        return ""
    token = raw.split("(")[0].strip()
    return token


def extract_spec_codes(raw: str) -> list[str]:
    """Extract valid spec_codes (e.g. 'M2.7') from a possibly-messy content_code string.

    Handles: 'P1.2', 'P2.3b' (invalid suffix -> dropped), 'MM7.1, MM7.2' (multi),
    'M6.1 (Interpret ...)' (parenthetical explanation -> stripped).
    """
    if not raw:
        return []
    out = []
    for part in re.split(r"\s*,\s*|\s+or\s+", raw):
        token = clean_code_token(part)
        # allow a bare match of the spec code pattern even if trailed by extra text
        m = re.match(r"^(MM[1-8]|M[1-7]|P[1-7]|B(1[01]|[1-9])|C(1[0-7]|[1-9]))\.\d+", token)
        if m and is_valid_spec_code(m.group(0)):
            out.append(m.group(0))
    # de-dupe, preserve order
    seen = set()
    result = []
    for c in out:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def extract_module_codes(raw: str) -> list[str]:
    """Extract module_code tokens (proposal Section 4.2 get_module_code), e.g.
    'M1 / P' -> ['M1', 'P']; 'M1 (assumed...)' -> ['M1']; 'N/A' -> [].
    """
    if not raw:
        return []
    if raw.strip().upper() in ("N/A", "OUT_OF_SPEC", ""):
        return []
    codes = []
    for part in re.split(r"\s*/\s*", raw):
        token = clean_code_token(part)
        if token and token.upper() not in ("N/A", ""):
            codes.append(token)
    return codes


TOPIC_LEVEL_LEADING_RE = re.compile(r"^(MM[1-8]|M[1-7]|P[1-7]|B(?:1[01]|[1-9])|C(?:1[0-7]|[1-9]))")


def extract_topic_codes(raw: str) -> list[str]:
    """Extract topic-level codes (e.g. 'M4', 'P3', 'MM1') from a possibly-messy
    topic_code (or module_code) string. Truncates finer-grain suffixes, e.g.
    'P2.2' -> 'P2', 'M5.18' -> 'M5', 'MM1.3' -> 'MM1'.
    """
    if not raw:
        return []
    if raw.strip().upper() in ("N/A", "OUT_OF_SPEC", ""):
        return []
    out = []
    for part in re.split(r"\s*/\s*|\s*,\s*|\s+or\s+", raw):
        token = clean_code_token(part)
        m = TOPIC_LEVEL_LEADING_RE.match(token)
        if m and m.group(1) in TOPIC_KEY_PREFIXES:
            out.append(m.group(1))
    seen = set()
    result = []
    for c in out:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def build_topic_keys(topic_code_raw: str, fallback_raw: str = "") -> list[str]:
    """Build topic_keys_json entries, preferring the enrichment topic_code
    field (Appendix C), falling back to module_code if topic_code is unusable.
    """
    codes = extract_topic_codes(topic_code_raw) or extract_topic_codes(fallback_raw)
    keys = [f"{TOPIC_KEY_PREFIXES[c]}.{c}" for c in codes]
    seen = set()
    result = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            result.append(k)
    return result


def condensed_summary() -> str:
    """Condensed taxonomy summary for LLM prompts (~2000 tokens)."""
    tax = load_taxonomy()
    lines = []
    for m in tax["modules"]:
        lines.append(f"### Module {m['code']}: {m['name']}")
        for t in m.get("topics", []):
            sub_codes = ", ".join(st["spec_code"] for st in t.get("subtopics", []))
            lines.append(f"- {t['spec_code']} {t['name']}: [{sub_codes}]")
    return "\n".join(lines)
