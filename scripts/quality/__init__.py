"""ESAT 4-gate quality verification stack.

Each module exposes a `check(question: dict) -> dict` function returning the
standard verdict dict:

    {
        "pass": bool,            # overall pass/fail
        "score": float,          # 0.0–1.0 (gate-specific meaning)
        "reason": str,           # short human-readable justification
        "issues": list[str],     # detailed findings (may be empty)
        "cost_usd": float,       # API cost incurred by this gate, USD
    }

Reference: ESA-17 §3 / ESA-22 spec, strategy §2.3,
`orchestration-review.md` Priorities #1 and #3.
"""

from .verdict import verdict  # re-exported convenience builder

__all__ = ["verdict"]
