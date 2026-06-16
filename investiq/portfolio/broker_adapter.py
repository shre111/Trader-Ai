"""
InvestIQ — broker seam.

A thin abstraction over order placement so the simulated `PaperBroker` can later
be swapped for a real broker without touching portfolio/rebalance logic. Mirrors
the reference project's execution/broker_adapter separation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from database.db import execute_sql, read_sql
from utils.logger import get_logger

logger = get_logger("broker")


class BrokerAdapter(ABC):
    mode = "base"

    @abstractmethod
    def place_order(self, symbol: str, side: str, units: float, price: float) -> dict: ...

    @abstractmethod
    def transactions(self) -> pd.DataFrame: ...


class PaperBroker(BrokerAdapter):
    """Simulated broker — records transactions to the DB, no real money."""

    mode = "paper"

    def place_order(self, symbol: str, side: str, units: float, price: float) -> dict:
        amount = round(float(units) * float(price), 2)
        execute_sql(
            """INSERT INTO portfolio_transactions (symbol, side, units, price, amount, mode)
               VALUES (:s, :sd, :u, :p, :a, 'paper')""",
            {"s": symbol, "sd": side, "u": float(units), "p": float(price), "a": amount},
        )
        logger.info(f"PAPER {side} {symbol}: {units:.4f} @ {price:.2f} = {amount:.2f}")
        return {"symbol": symbol, "side": side, "units": units, "price": price, "amount": amount}

    def transactions(self) -> pd.DataFrame:
        return read_sql("SELECT * FROM portfolio_transactions WHERE mode='paper' ORDER BY ts, id")

    def reset(self):
        execute_sql("DELETE FROM portfolio_transactions WHERE mode='paper'")
        logger.info("Paper transactions cleared.")


class LiveBroker(BrokerAdapter):
    """Placeholder for a real broker integration (intentionally not wired)."""

    mode = "live"

    def place_order(self, *args, **kwargs):
        raise NotImplementedError("Live broker is not wired — InvestIQ runs paper-only for now.")

    def transactions(self) -> pd.DataFrame:
        raise NotImplementedError("Live broker is not wired — InvestIQ runs paper-only for now.")
