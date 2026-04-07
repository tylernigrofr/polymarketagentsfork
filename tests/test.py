"""
% python test/test.py
...
----------------------------------------------------------------------
Ran 3 tests in 0.000s

OK
"""

import unittest


from agents.execution.modes import ExecutionMode
from agents.execution.risk import RiskLimits, compute_trade_usdc_amount, validate_ticket
from agents.execution.ticket import TradeIntent, TradeTicket


class DummyPolymarket:
    def __init__(self, balance: float) -> None:
        self._balance = balance

    def get_usdc_balance(self) -> float:
        return self._balance


class TestExecutionSafety(unittest.TestCase):
    def test_execution_mode_enum(self):
        self.assertEqual(ExecutionMode("dry_run"), ExecutionMode.DRY_RUN)
        self.assertEqual(ExecutionMode("paper"), ExecutionMode.PAPER)

    def test_compute_trade_amount_respects_caps(self):
        limits = RiskLimits(max_usdc_per_trade=5.0, max_fraction_balance_per_trade=0.05)
        # balance=200 => 5% cap is 10, absolute cap is 5 => cap is 5
        amt = compute_trade_usdc_amount(
            balance_usdc=200.0, proposed_fraction=0.5, limits=limits
        )
        self.assertEqual(amt, 5.0)

    def test_validate_ticket_rejects_missing_intent(self):
        ticket = TradeTicket.new(mode="dry_run", runtime={})
        res = validate_ticket(
            ticket=ticket, polymarket=DummyPolymarket(100.0), limits=RiskLimits()
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["reason"], "missing_intent")

    def test_validate_ticket_rejects_over_fraction_balance(self):
        limits = RiskLimits(
            max_usdc_per_trade=1000.0, max_fraction_balance_per_trade=0.05
        )
        ticket = TradeTicket.new(mode="dry_run", runtime={})
        ticket.intent = TradeIntent(side="BUY", amount_usdc=6.0)
        res = validate_ticket(
            ticket=ticket, polymarket=DummyPolymarket(100.0), limits=limits
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["reason"], "max_fraction_balance_per_trade_exceeded")


if __name__ == "__main__":
    unittest.main()
