from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from agents.execution.modes import ExecutionMode
from agents.execution.risk import RiskLimits
from agents.execution.risk import validate_ticket
from agents.execution.ticket import TradeTicket


class TradeExecutor:
    def __init__(
        self,
        polymarket_client: Any,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
        risk: Optional[RiskLimits] = None,
    ) -> None:
        self.polymarket = polymarket_client
        self.mode = mode
        self.risk = risk or RiskLimits()

    def execute(self, ticket: TradeTicket) -> Dict[str, Any]:
        """
        Execute or simulate a trade described by a TradeTicket.

        - DRY_RUN: validate + return intent only
        - PAPER: validate + record simulated fill (placeholder for now)
        - LIVE: validate + post order through Polymarket client (wired later)
        """
        now = datetime.now(tz=timezone.utc).isoformat()

        validation = validate_ticket(
            ticket=ticket, polymarket=self.polymarket, limits=self.risk
        )
        if not validation["ok"]:
            return {
                "timestamp": now,
                "mode": self.mode.value,
                "status": "REJECTED",
                "reason": validation["reason"],
                "ticket": ticket.model_dump(),
            }

        if self.mode == ExecutionMode.DRY_RUN:
            return {
                "timestamp": now,
                "mode": self.mode.value,
                "status": "DRY_RUN",
                "ticket": ticket.model_dump(),
            }

        if self.mode == ExecutionMode.PAPER:
            # Placeholder: actual paper fill simulation will be implemented in tracking layer.
            return {
                "timestamp": now,
                "mode": self.mode.value,
                "status": "PAPER",
                "ticket": ticket.model_dump(),
                "fill": {
                    "simulated": True,
                    "price": ticket.target_price,
                    "notional_usdc": ticket.notional_usdc,
                },
            }

        if self.mode == ExecutionMode.LIVE:
            # LIVE execution is intentionally conservative: keep as explicit wiring step.
            # This will be implemented when integrating order types and slippage controls.
            raise RuntimeError("LIVE execution is not wired yet. Use DRY_RUN or PAPER.")

        raise RuntimeError(f"Unknown execution mode: {self.mode}")
