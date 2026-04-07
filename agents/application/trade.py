import os
from typing import Optional

from agents.application.executor import Executor as Agent
from agents.execution.executor import TradeExecutor
from agents.execution.modes import ExecutionMode
from agents.execution.risk import RiskLimits, compute_trade_usdc_amount
from agents.execution.ticket import TradeIntent, TradeTicket
from agents.metrics.ledger import append_jsonl
from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.polymarket.polymarket import Polymarket

import shutil


class Trader:
    def __init__(self):
        self.polymarket = Polymarket()
        self.gamma = Gamma()
        self.agent = Agent()

    def pre_trade_logic(self) -> None:
        self.clear_local_dbs()

    def clear_local_dbs(self) -> None:
        try:
            shutil.rmtree("local_db_events")
        except:
            pass
        try:
            shutil.rmtree("local_db_markets")
        except:
            pass

    def one_best_trade(
        self,
        mode: Optional[str] = None,
        max_usdc_per_trade: float = 5.0,
        max_fraction_balance_per_trade: float = 0.05,
        runs_dir: str = "runs",
    ) -> dict:
        """

        one_best_trade is a strategy that evaluates all events, markets, and orderbooks

        leverages all available information sources accessible to the autonomous agent

        then executes that trade without any human intervention

        """
        mode = (mode or os.getenv("EXECUTION_MODE") or "dry_run").lower()
        exec_mode = ExecutionMode(mode)
        risk = RiskLimits(
            max_usdc_per_trade=max_usdc_per_trade,
            max_fraction_balance_per_trade=max_fraction_balance_per_trade,
        )
        executor = TradeExecutor(
            polymarket_client=self.polymarket, mode=exec_mode, risk=risk
        )

        self.pre_trade_logic()

        events = self.polymarket.get_all_tradeable_events()
        print(f"1. FOUND {len(events)} EVENTS")

        filtered_events = self.agent.filter_events_with_rag(events)
        print(f"2. FILTERED {len(filtered_events)} EVENTS")

        markets = self.agent.map_filtered_events_to_markets(filtered_events)
        print()
        print(f"3. FOUND {len(markets)} MARKETS")

        print()
        filtered_markets = self.agent.filter_markets(markets)
        print(f"4. FILTERED {len(filtered_markets)} MARKETS")

        market = filtered_markets[0]
        trade_ctx = self.agent.source_best_trade_context(market)
        print(f"5. CALCULATED TRADE {trade_ctx['proposal_raw']}")

        # Compute amount using balance + proposal size fraction (clamped by risk limits).
        balance_usdc = float(self.polymarket.get_usdc_balance())
        proposal = trade_ctx["proposal"]
        amount_usdc = compute_trade_usdc_amount(
            balance_usdc=balance_usdc,
            proposed_fraction=proposal.size_fraction,
            limits=risk,
        )

        ticket = TradeTicket.new(
            mode=exec_mode.value,
            runtime=trade_ctx.get("runtime", {}),
        )
        ticket.market_id = trade_ctx.get("market_id")
        ticket.target_price = proposal.price
        ticket.proposal_raw = trade_ctx["proposal_raw"]
        ticket.notional_usdc = amount_usdc
        ticket.intent = TradeIntent(side=proposal.side, amount_usdc=amount_usdc)

        result = executor.execute(ticket)
        ticket.result = result
        print(f"6. EXECUTION RESULT {result.get('status')}")
        append_jsonl(runs_dir, "trade_tickets.jsonl", ticket.model_dump())
        return result

    def maintain_positions(self):
        pass

    def incentive_farm(self):
        pass


if __name__ == "__main__":
    t = Trader()
    t.one_best_trade()
