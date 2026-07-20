"""
InvestIQ — synthetic dataset generator.

Produces a small, self-contained investing universe (mutual funds + equities + a
benchmark index) with ~4 years of daily NAV/price series and equity fundamentals.
Lets the full pipeline (features → ML → scoring → portfolio) be built and tested
with no network or real data — the investing-domain analog of the reference
project's `mock` mode.

Output DataFrames match the `database/schema.sql` columns so they load via
`upsert_rows` directly.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

# Benchmark used by every mock security.
MOCK_BENCHMARK = "^MOCKNIFTY"

# (symbol, name, sec_type, category, fund_house, scheme_code, start_price,
#  annual_drift, annual_vol, seed)
_UNIVERSE = [
    # Benchmark index
    ("^MOCKNIFTY", "Mock Nifty Index", "INDEX", "Index", None, None, 18000, 0.11, 0.15, 1),
    # Mutual funds (keyed by scheme_code in nav_history)
    ("MF0001", "Mock Flexi Cap Fund", "MF", "Flexi Cap", "Mock AMC", "MF0001", 100, 0.14, 0.17, 2),
    ("MF0002", "Mock Large Cap Fund", "MF", "Large Cap", "Mock AMC", "MF0002", 80, 0.11, 0.13, 3),
    ("MF0003", "Mock Small Cap Fund", "MF", "Small Cap", "Mock AMC", "MF0003", 50, 0.18, 0.28, 4),
    # Equities (keyed by symbol in price_history)
    ("MOCKTECH.NS", "MockTech Ltd", "EQUITY", "IT", None, None, 1500, 0.20, 0.26, 5),
    ("MOCKBANK.NS", "MockBank Ltd", "EQUITY", "Financials", None, None, 950, 0.13, 0.22, 6),
    ("MOCKPHARMA.NS", "MockPharma Ltd", "EQUITY", "Healthcare", None, None, 700, 0.10, 0.19, 7),
    ("MOCKENERGY.NS", "MockEnergy Ltd", "EQUITY", "Energy", None, None, 2400, 0.08, 0.21, 8),
]

# Plausible static fundamentals per equity (pe, pb, roe, debt_equity, div_yield, sector).
_FUNDAMENTALS = {
    "MOCKTECH.NS": (32.0, 9.5, 0.27, 0.05, 0.010, "IT"),
    "MOCKBANK.NS": (16.0, 2.4, 0.16, 0.80, 0.012, "Financials"),
    "MOCKPHARMA.NS": (28.0, 5.1, 0.19, 0.20, 0.008, "Healthcare"),
    "MOCKENERGY.NS": (12.0, 1.6, 0.13, 0.55, 0.030, "Energy"),
}


def _gbm_series(n_days: int, start_price: float, drift: float, vol: float, seed: int) -> np.ndarray:
    """Geometric Brownian Motion daily close series."""
    rng = np.random.default_rng(seed)
    dt = 1.0 / 252.0
    steps = rng.normal((drift - 0.5 * vol**2) * dt, vol * np.sqrt(dt), n_days)
    return np.exp(np.log(start_price) + np.cumsum(steps))


def generate_all_mock_data(years: float = 4.0, end: date | None = None) -> dict:
    """
    Generate the full mock dataset.

    Returns dict with keys: securities, nav_history, price_history, fundamentals
    (all pandas DataFrames ready for upsert_rows).
    """
    end = end or date.today()
    n_days = int(252 * years)
    dates = pd.bdate_range(end=pd.Timestamp(end), periods=n_days).date

    securities, nav_rows, price_rows, fund_rows = [], [], [], []

    for (symbol, name, sec_type, category, fund_house, scheme_code,
         start_price, drift, vol, seed) in _UNIVERSE:
        securities.append({
            "symbol": symbol, "name": name, "sec_type": sec_type,
            "category": category, "fund_house": fund_house,
            "benchmark": MOCK_BENCHMARK, "scheme_code": scheme_code, "active": True,
        })

        closes = _gbm_series(n_days, start_price, drift, vol, seed)

        if sec_type == "MF":
            for d, nav in zip(dates, closes):
                nav_rows.append({"date": d, "scheme_code": scheme_code, "nav": round(float(nav), 4)})
        else:  # EQUITY / INDEX → OHLCV
            rng = np.random.default_rng(seed + 100)
            for i, (d, close) in enumerate(zip(dates, closes)):
                prev = closes[i - 1] if i > 0 else close
                hi = close * (1 + abs(rng.normal(0, 0.004)))
                lo = close * (1 - abs(rng.normal(0, 0.004)))
                op = float(np.clip(prev * (1 + rng.normal(0, 0.003)), lo, hi))
                price_rows.append({
                    "date": d, "symbol": symbol,
                    "open": round(op, 2), "high": round(float(hi), 2),
                    "low": round(float(lo), 2), "close": round(float(close), 2),
                    "adj_close": round(float(close), 2),
                    "volume": int(rng.integers(1_000_00, 5_000_00)),
                })

        if symbol in _FUNDAMENTALS:
            pe, pb, roe, de, dy, sector = _FUNDAMENTALS[symbol]
            mcap = float(closes[-1]) * 1e8  # arbitrary but stable
            fund_rows.append({
                "date": dates[-1], "symbol": symbol, "pe": pe, "pb": pb,
                "peg": round(pe / 15.0, 2), "roe": roe, "debt_equity": de,
                "eps": round(float(closes[-1]) / pe, 2), "div_yield": dy,
                "market_cap": round(mcap, 0), "sector": sector,
            })

    return {
        "securities": pd.DataFrame(securities),
        "nav_history": pd.DataFrame(nav_rows),
        "price_history": pd.DataFrame(price_rows),
        "fundamentals": pd.DataFrame(fund_rows),
    }


def load_mock_data_to_db() -> dict:
    """Generate the mock dataset and upsert it into the investiq DB. Returns row counts."""
    from database.db import upsert_rows  # lazy import (DB only needed when loading)

    data = generate_all_mock_data()
    counts = {
        "securities": upsert_rows(data["securities"], "securities", ["symbol"], update=True),
        "nav_history": upsert_rows(data["nav_history"], "nav_history", ["date", "scheme_code"]),
        "price_history": upsert_rows(data["price_history"], "price_history", ["date", "symbol"]),
        "fundamentals": upsert_rows(data["fundamentals"], "fundamentals", ["date", "symbol"], update=True),
    }
    return counts
