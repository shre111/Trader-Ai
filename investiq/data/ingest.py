"""
InvestIQ — ingestion orchestrator.

Pulls the configured universe (Nifty 50 equities + many mutual funds + benchmark)
from free sources into the investiq DB. All writes go through `upsert_rows`, so
re-runs are idempotent and a daily `refresh()` simply fills new rows.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from config.universe import BENCHMARK, FUND_TARGETS, NIFTY50
from data.mfapi_adapter import fetch_nav_history, resolve_scheme
from data.yfinance_adapter import fetch_fundamentals, fetch_price_history
from database.db import upsert_rows
from utils.logger import get_logger

logger = get_logger("ingest")


def _display_name(ticker: str) -> str:
    if ticker == BENCHMARK:
        return "Nifty 50"
    return ticker.replace(".NS", "").replace(".BO", "")


def ingest_securities(tickers, sec_type: str, with_fundamentals: bool, period: str) -> int:
    """Ingest price history (+ optional fundamentals) for equity/index tickers."""
    sec_rows, fund_rows, price_total = [], [], 0
    for tk in tickers:
        try:
            ph = fetch_price_history(tk, period=period)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"  {tk}: price fetch failed ({e})")
            continue
        if ph.empty:
            logger.warning(f"  {tk}: no price data")
            continue
        ph = ph.copy()
        ph["symbol"] = tk
        price_total += upsert_rows(ph, "price_history", ["date", "symbol"])
        sec_rows.append({
            "symbol": tk, "name": _display_name(tk), "sec_type": sec_type,
            "benchmark": BENCHMARK, "active": True,
        })
        if with_fundamentals:
            f = fetch_fundamentals(tk)
            f.update({"date": date.today(), "symbol": tk})
            fund_rows.append(f)
        logger.info(f"  {tk}: {len(ph)} price rows")

    if sec_rows:
        upsert_rows(pd.DataFrame(sec_rows), "securities", ["symbol"], update=True)
    if fund_rows:
        upsert_rows(pd.DataFrame(fund_rows), "fundamentals", ["date", "symbol"], update=True)
    return price_total


def ingest_funds(targets) -> int:
    """Resolve fund targets to scheme codes and ingest their NAV history."""
    sec_rows, nav_total = [], 0
    for name, category in targets:
        scheme = resolve_scheme(name)
        if not scheme:
            logger.warning(f"  no scheme match: {name}")
            continue
        code = str(scheme["schemeCode"])
        try:
            nav, meta = fetch_nav_history(code)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"  {name} [{code}]: NAV fetch failed ({e})")
            continue
        if nav.empty:
            logger.warning(f"  {name} [{code}]: no NAV data")
            continue
        nav = nav.copy()
        nav["scheme_code"] = code
        nav_total += upsert_rows(nav, "nav_history", ["date", "scheme_code"])
        sec_rows.append({
            "symbol": code, "name": (meta.get("scheme_name") or name)[:200], "sec_type": "MF",
            "category": meta.get("scheme_category") or category,
            "fund_house": meta.get("fund_house"), "benchmark": BENCHMARK,
            "scheme_code": code, "active": True,
        })
        logger.info(f"  {(meta.get('scheme_name') or name)[:48]} [{code}]: {len(nav)} NAV rows")

    if sec_rows:
        upsert_rows(pd.DataFrame(sec_rows), "securities", ["symbol"], update=True)
    return nav_total


def run_ingest(sample: bool = False, period: str = "5y") -> dict:
    """Ingest the full (or --sample) universe. Returns row counts."""
    tickers = NIFTY50[:3] if sample else NIFTY50
    funds = FUND_TARGETS[:2] if sample else FUND_TARGETS

    logger.info("Ingesting benchmark index ...")
    ingest_securities([BENCHMARK], "INDEX", with_fundamentals=False, period=period)
    logger.info(f"Ingesting {len(tickers)} equities ...")
    pc = ingest_securities(tickers, "EQUITY", with_fundamentals=True, period=period)
    logger.info(f"Ingesting {len(funds)} mutual funds ...")
    nc = ingest_funds(funds)

    # New rows landed, so any cached price snapshot is now out of date.
    from portfolio.paper_portfolio import invalidate_price_cache

    invalidate_price_cache()

    logger.info(f"Ingest complete: +{pc} price rows, +{nc} NAV rows")
    return {"price_rows": pc, "nav_rows": nc}


def refresh(period: str = "1mo") -> dict:
    """Lightweight daily refresh — pull recent prices/NAV and upsert (dedup-safe)."""
    logger.info("Refreshing universe (recent window) ...")
    return run_ingest(sample=False, period=period)
