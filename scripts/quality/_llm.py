"""Shared LLM client for LLM-backed quality gates.

The LLM-backed gates (`solver`, `reviewer`, `bio_judge`) use GLM-5.2 via
the z.ai OpenAI-compatible API. This helper centralises:

- client construction (reuses z.ai API key from generator_glm)
- exponential backoff on rate limits / transient errors
- cost estimation
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# z.ai GLM-5.2 via OpenAI-compatible SDK (free tier).
try:
    import openai as _openai_module  # type: ignore
except ImportError:
    _openai_module = None  # type: ignore

MODEL_PRICING: dict[str, dict[str, float]] = {
    "glm-5.2": {"input": 0.0, "output": 0.0},
}

DEFAULT_MODEL = "glm-5.2"

MAX_RETRIES = 4
RETRY_BASE_DELAY = 1.5  # seconds, doubled each retry

_client = None  # module-level singleton


def _get_client():
    """Build (once) an OpenAI-compatible client pointed at z.ai."""
    global _client
    if _client is not None:
        return _client
    if _openai_module is None:
        raise RuntimeError("openai SDK not installed — run `pip install openai`")
    # Resolve API key the same way generator_glm does.
    SCRIPTS_DIR = Path(__file__).resolve().parent
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import generator_glm
    api_key = generator_glm.resolve_api_key(None)
    if not api_key:
        raise RuntimeError("z.ai API key not available (set ZAI_API_KEY)")
    _client = _openai_module.OpenAI(api_key=api_key, base_url=generator_glm.ZAI_BASE_URL)
    return _client


@dataclass
class LLMResult:
    text: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    model: str


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
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
    """Make a single GLM-5.2 call via z.ai with retry/backoff.

    Function name kept as `call_haiku` for backward compatibility with
    existing imports in solver, reviewer, and bio_judge.
    `cache_system_prompt` is accepted but ignored (no-op for z.ai).
    """
    if _openai_module is None:
        raise RuntimeError("openai SDK not installed")

    client = _get_client()
    effective_model = model or DEFAULT_MODEL

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=effective_model,
                messages=[
                    {"role": "system", "content": system_prompt} if system_prompt else None,
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = response.choices[0].message.content or "" if response.choices else ""

            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

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
            delay = RETRY_BASE_DELAY * (2 ** attempt) + 0.5
            logger.warning(
                "GLM call failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, delay, last_exc,
            )
            time.sleep(delay)

    raise RuntimeError(f"GLM call failed after {MAX_RETRIES} attempts: {last_exc}")
