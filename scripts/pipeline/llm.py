"""z.ai (GLM) LLM client for the corpus enrichment pipeline.

Key resolution order (matches the pattern used by existing scripts/latex-cleanup-*.py):
  1. ZAI_API_KEY env var
  2. scripts/.openai-api-key file
  3. openclaw agent auth store (esat-manager / main)
"""

import json
import os
import random
import re
import sqlite3
import time
from pathlib import Path

import openai

ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REQUEST_TIMEOUT = 60.0  # seconds; z.ai calls have hung indefinitely without this

OPENCLAW_AUTH_DBS = [
    Path.home() / ".openclaw" / "agents" / "esat-manager" / "agent" / "openclaw-agent.sqlite",
    Path.home() / ".openclaw" / "agents" / "main" / "agent" / "openclaw-agent.sqlite",
]


def _get_zai_api_key() -> str:
    env_key = os.environ.get("ZAI_API_KEY")
    if env_key:
        return env_key

    key_file = SCRIPTS_DIR / ".openai-api-key"
    if key_file.exists():
        candidate = key_file.read_text().strip()
        if candidate:
            try:
                client = openai.OpenAI(api_key=candidate, base_url=ZAI_BASE_URL, timeout=REQUEST_TIMEOUT)
                client.chat.completions.create(
                    model="glm-4.7", messages=[{"role": "user", "content": "ping"}], max_tokens=1
                )
                return candidate
            except Exception:
                pass  # fall through to openclaw store

    for db_path in OPENCLAW_AUTH_DBS:
        if not db_path.exists():
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT store_json FROM auth_profile_store WHERE store_key = ?", ("primary",))
            row = cur.fetchone()
            conn.close()
            if row:
                data = json.loads(row[0])
                key = data.get("profiles", {}).get("zai:default", {}).get("key")
                if key:
                    return key
        except Exception:
            continue

    raise RuntimeError("No working z.ai API key found (checked env, key file, openclaw store)")


_client = None


def get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        _client = openai.OpenAI(api_key=_get_zai_api_key(), base_url=ZAI_BASE_URL, timeout=REQUEST_TIMEOUT)
    return _client


def call_glm(
    prompt: str,
    model: str = "glm-4.7",
    max_tokens: int = 4096,
    temperature: float = 0.1,
    max_retries: int = 4,
    base_delay: float = 5.0,
) -> str | None:
    """Call z.ai GLM with retry + exponential backoff. Returns raw text or None."""
    client = get_client()
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  [llm] failed after {max_retries} attempts: {e}")
                return None
            delay = base_delay * (2**attempt) + random.uniform(0, 1)
            print(f"  [llm] attempt {attempt + 1} failed ({e}); retrying in {delay:.1f}s")
            time.sleep(delay)
    return None


def extract_json(text: str):
    """Extract the first valid JSON value (object or array) from an LLM response."""
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # find the first balanced {...} or [...] block
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start = text.find(open_c)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == open_c:
                depth += 1
            elif text[i] == close_c:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break
    return None
