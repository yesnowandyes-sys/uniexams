"""Shared LLM client for the Haiku-backed quality gates.

The three LLM-backed gates (`solver`, `reviewer`, `bio_judge`) all use the
Anthropic Messages API via the proxy configured in the environment
(`ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`).
This helper centralises:

- client construction
- prompt-cache wiring for long static context (Bio Content Spec PDF)
- exponential backoff on rate limits / transient errors
- cost estimation from `response.usage`

Per `orchestration-review.md` §3, the Bio Content Spec is loaded once and
cached across calls — this is the bulk of the cost saving that keeps the
total 4-gate cost ≤ $0.005 / question.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

try:
    from google import genai
    from google.genai.types import GenerateContentConfig
except ImportError:  # pragma: no cover
    genai = None  # type: ignore

logger = logging.getLogger(__name__)


# Per-message model pricing (USD per million tokens).
# Gemini free tier = $0. Paid tier rates shown for reference.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.0, "output": 0.0},
    "gemini-2.5-pro": {"input": 0.0, "output": 0.0},
    "gemini-2.5-flash-paid": {"input": 0.30, "output": 2.40},
    "gemini-2.5-pro-paid": {"input": 1.25, "output": 10.0},
    # Legacy pricing (kept for reference)
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0, "cache_write": 1.25, "cache_read": 0.10},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.0, "cache_write": 1.0, "cache_read": 0.08},
    "glm-4.5-air": {"input": 0.0, "output": 0.0, "cache_write": 0.0, "cache_read": 0.0},
    "glm-5.2": {"input": 0.0, "output": 0.0, "cache_write": 0.0, "cache_read": 0.0},
}

# Primary API key from environment; fallback provided if quota exhausted.
PRIMARY_API_KEY = os.environ.get("GEMINI_API_KEY")
FALLBACK_API_KEY = "AIzaSyBkiGJSS45VVKwZuTL6oXPl-K3_Qv9z-44"  # Provided 2026-07-20
DEFAULT_MODEL = os.environ.get("QUALITY_GATE_MODEL") or "gemini-2.5-flash"

MAX_RETRIES = 4
RETRY_BASE_DELAY = 1.5  # seconds, doubled each retry


def _is_quota_error(exc: Exception) -> bool:
    """Check if exception is a quota/rate-limit error (429)."""
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    if status == 429:
        return True
    msg = str(exc).lower()
    if "quota exceeded" in msg or "resource_exhausted" in msg:
        return True
    return False


@dataclass
class LLMResult:
    text: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    model: str


def _price(model: str) -> dict[str, float]:
    return MODEL_PRICING.get(
        model, {"input": 0.30, "output": 2.40, "cache_write": 0.0, "cache_read": 0.0}
    )


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = _price(model)
    return (
        input_tokens * p["input"] / 1_000_000
        + output_tokens * p["output"] / 1_000_000
    )


def call_haiku(
    *,
    user_prompt: str,
    system_prompt: str = "",
    model: Optional[str] = None,
    max_tokens: int = 2048,
    cache_system_prompt: bool = False,
    temperature: float = 0.0,
) -> LLMResult:
    """Make a single Gemini call with retry/backoff.

    Replaces the previous Anthropic Haiku path. Uses google-genai SDK
    with GEMINI_API_KEY. The cache_system_prompt parameter is accepted
    for backward compatibility but is a no-op (Gemini handles caching
    automatically via implicit context caching).
    """
    if genai is None:
        raise RuntimeError(
            "google-genai SDK not installed — run `pip install google-genai`"
        )

    api_key = PRIMARY_API_KEY or FALLBACK_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)

    # Track which key we're using for fallback switching
    using_primary = (api_key == PRIMARY_API_KEY) and PRIMARY_API_KEY is not None
    effective_model = model or DEFAULT_MODEL

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            config = GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
            response = client.models.generate_content(
                model=effective_model,
                contents=user_prompt,
                config=config,
            )
            text = response.text or ""

            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0 if usage else 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0 if usage else 0

            cost = _estimate_cost(effective_model, input_tokens, output_tokens)
            return LLMResult(
                text=text,
                cost_usd=cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=0,
                cache_creation_tokens=0,
                model=effective_model,
            )
        except Exception as exc:
            last_exc = exc
            # Check if it's a quota error and we have a fallback key
            if _is_quota_error(exc) and using_primary and FALLBACK_API_KEY:
                logger.warning(
                    "Primary API key quota exhausted, switching to fallback"
                )
                # Retry with fallback key
                client = genai.Client(api_key=FALLBACK_API_KEY)
                using_primary = False
                continue
            
            delay = RETRY_BASE_DELAY * (2 ** attempt) + 0.5
            logger.warning(
                "Gemini call failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, delay, last_exc,
            )
            time.sleep(delay)

    raise RuntimeError(f"Gemini call failed after {MAX_RETRIES} attempts: {last_exc}")
