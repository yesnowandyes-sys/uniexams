"""Standard verdict builder shared across all quality gates."""

from __future__ import annotations

from typing import Any, Iterable


def verdict(
    *,
    passed: bool,
    score: float,
    reason: str,
    issues: Iterable[str] | None = None,
    cost_usd: float = 0.0,
    **extra: Any,
) -> dict[str, Any]:
    """Construct the standard `{pass, score, reason, issues, cost_usd}` dict.

    Extra keyword arguments are merged into the dict so individual gates can
    attach gate-specific diagnostics (e.g. `atoms_balanced`, `solver_choice`)
    without breaking the shared contract.
    """
    score = float(score)
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"score must be in [0,1]; got {score}")
    out: dict[str, Any] = {
        "pass": bool(passed),
        "score": score,
        "reason": str(reason),
        "issues": list(issues or []),
        "cost_usd": float(cost_usd),
    }
    out.update(extra)
    return out
