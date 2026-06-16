"""
InvestIQ — paper portfolio.

Tracks a simulated portfolio from the recorded transactions: holdings (average
cost, market value, P&L, weight), cash, total value, and daily snapshots for the
equity curve. Prices are the latest close (equities/indices) or NAV (funds).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from config.settings import INITIAL_CAPITAL
from database.db import read_sql, upsert_rows
from portfolio.broker_adapter import BrokerAdapter, PaperBroker
from utils.logger import get_logger

logger = get_logger("portfolio")

_HOLD_COLS = ["symbol", "units", "avg_cost", "price", "value", "cost", "pnl", "pnl_pct", "weight"]


def latest_prices() -> dict:
    """symbol → latest price (close for equities/indices, NAV for funds)."""
    eq = read_sql(
        """SELECT p.symbol, p.close AS price FROM price_history p
           JOIN (SELECT symbol, max(date) d FROM price_history GROUP BY symbol) m
             ON p.symbol = m.symbol AND p.date = m.d"""
    )
    mf = read_sql(
        """SELECT s.symbol, n.nav AS price FROM securities s
           JOIN (SELECT scheme_code, max(date) d FROM nav_history GROUP BY scheme_code) m
             ON s.scheme_code = m.scheme_code
           JOIN nav_history n ON n.scheme_code = s.scheme_code AND n.date = m.d
           WHERE s.sec_type = 'MF'"""
    )
    prices = dict(zip(eq["symbol"], eq["price"]))
    prices.update(dict(zip(mf["symbol"], mf["price"])))
    return prices


class PaperPortfolio:
    def __init__(self, broker: BrokerAdapter | None = None, initial_capital: float = INITIAL_CAPITAL):
        self.broker = broker or PaperBroker()
        self.initial_capital = initial_capital

    def buy(self, symbol: str, amount: float, price: float | None = None):
        price = price or latest_prices().get(symbol)
        if not price:
            logger.warning(f"buy skipped — no price for {symbol}")
            return None
        amount = min(amount, self.cash())  # never spend more than available cash
        if amount <= 0:
            return None
        return self.broker.place_order(symbol, "BUY", amount / price, price)

    def sell(self, symbol: str, fraction: float = 1.0, price: float | None = None):
        h = self.holdings()
        row = h[h["symbol"] == symbol]
        if row.empty:
            return None
        units = float(row["units"].iloc[0]) * max(0.0, min(1.0, fraction))
        price = price or latest_prices().get(symbol)
        if not price or units <= 0:
            return None
        return self.broker.place_order(symbol, "SELL", units, price)

    def holdings(self) -> pd.DataFrame:
        tx = self.broker.transactions()
        if tx.empty:
            return pd.DataFrame(columns=_HOLD_COLS)
        prices = latest_prices()
        rows = []
        for sym, g in tx.groupby("symbol"):
            buy_units = g.loc[g["side"] == "BUY", "units"].sum()
            sell_units = g.loc[g["side"] == "SELL", "units"].sum()
            net = buy_units - sell_units
            if net <= 1e-9:
                continue
            avg_cost = g.loc[g["side"] == "BUY", "amount"].sum() / buy_units if buy_units else 0.0
            price = prices.get(sym, avg_cost)
            value, cost = net * price, net * avg_cost
            rows.append({
                "symbol": sym, "units": net, "avg_cost": avg_cost, "price": price,
                "value": value, "cost": cost, "pnl": value - cost,
                "pnl_pct": (value / cost - 1) if cost else 0.0,
            })
        h = pd.DataFrame(rows, columns=[c for c in _HOLD_COLS if c != "weight"])
        if not h.empty:
            tv = h["value"].sum()
            h["weight"] = h["value"] / tv if tv else 0.0
        return h

    def cash(self) -> float:
        tx = self.broker.transactions()
        if tx.empty:
            return self.initial_capital
        bought = tx.loc[tx["side"] == "BUY", "amount"].sum()
        sold = tx.loc[tx["side"] == "SELL", "amount"].sum()
        return self.initial_capital - bought + sold

    def summary(self) -> dict:
        h = self.holdings()
        invested = float(h["value"].sum()) if not h.empty else 0.0
        cash = self.cash()
        total = cash + invested
        pnl = total - self.initial_capital
        return {
            "total_value": total, "invested": invested, "cash": cash,
            "pnl": pnl, "pnl_pct": pnl / self.initial_capital if self.initial_capital else 0.0,
            "n_holdings": int(len(h)),
        }

    def snapshot(self, d: date | None = None) -> dict:
        d = d or date.today()
        s = self.summary()
        upsert_rows(
            pd.DataFrame([{
                "date": d, "mode": self.broker.mode, "total_value": s["total_value"],
                "invested": s["invested"], "cash": s["cash"], "pnl": s["pnl"],
            }]),
            "portfolio_snapshots", ["date", "mode"], update=True,
        )
        return s
