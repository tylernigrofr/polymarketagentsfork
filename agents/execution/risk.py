from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Set


@dataclass(frozen=True)
class RiskLimits:
    max_usdc_per_trade: float = 5.0
    max_fraction_balance_per_trade: float = 0.05
    min_liquidity: Optional[float] = None
    max_spread: Optional[float] = None
    allow_market_ids: Optional[Set[int]] = None


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_trade_usdc_amount(
    *,
    balance_usdc: float,
    proposed_fraction: float,
    limits: RiskLimits,
) -> float:
    proposed_fraction = clamp(proposed_fraction, 0.0, 1.0)
    cap_by_fraction = limits.max_fraction_balance_per_trade * max(balance_usdc, 0.0)
    cap = min(limits.max_usdc_per_trade, cap_by_fraction)
    return clamp(proposed_fraction * balance_usdc, 0.0, cap)


def is_market_allowed(*, market_id: int, limits: RiskLimits) -> bool:
    if limits.allow_market_ids is None:
        return True
    return market_id in limits.allow_market_ids


def validate_ticket(
    *, ticket: Any, polymarket: Any, limits: RiskLimits
) -> Dict[str, Any]:
    # Keep this permissive: ticket is a Pydantic model but we avoid importing it here.
    intent = getattr(ticket, "intent", None)
    if intent is None:
        return {"ok": False, "reason": "missing_intent"}

    amount = float(getattr(intent, "amount_usdc", 0.0) or 0.0)
    if amount <= 0:
        return {"ok": False, "reason": "non_positive_amount"}

    if amount > limits.max_usdc_per_trade:
        return {"ok": False, "reason": "max_usdc_per_trade_exceeded"}

    try:
        balance = float(polymarket.get_usdc_balance())
    except Exception:
        balance = 0.0

    if balance > 0 and amount > (limits.max_fraction_balance_per_trade * balance):
        return {"ok": False, "reason": "max_fraction_balance_per_trade_exceeded"}

    market_id = getattr(intent, "market_id", None)
    if market_id is not None and not is_market_allowed(
        market_id=int(market_id), limits=limits
    ):
        return {"ok": False, "reason": "market_not_allowlisted"}

    return {"ok": True, "reason": "ok"}
