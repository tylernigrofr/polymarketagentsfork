from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class TradeIntent(BaseModel):
    side: Literal["BUY", "SELL"]
    amount_usdc: float = Field(..., ge=0.0)
    market_id: Optional[int] = None
    token_id: Optional[str] = None


class TradeTicket(BaseModel):
    ticket_id: str
    created_at: str
    mode: str

    market_id: Optional[int] = None
    target_price: Optional[float] = None
    notional_usdc: Optional[float] = None

    runtime: Dict[str, Any] = Field(default_factory=dict)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    forecast: Dict[str, Any] = Field(default_factory=dict)
    proposal_raw: Optional[str] = None
    decision: Dict[str, Any] = Field(default_factory=dict)

    intent: Optional[TradeIntent] = None
    result: Dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def new(mode: str, runtime: Dict[str, Any]) -> "TradeTicket":
        now = datetime.now(timezone.utc).isoformat()
        ticket_id = f"ticket_{int(datetime.now(timezone.utc).timestamp())}"
        return TradeTicket(
            ticket_id=ticket_id, created_at=now, mode=mode, runtime=runtime
        )
