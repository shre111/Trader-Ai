"""
InvestIQ — Yahoo Finance adapter (free, delayed/EOD equity data) via yfinance.

Fetches end-of-day OHLCV history and a best-effort fundamentals snapshot. Yahoo's
`.info` is slow and occasionally flaky, so fundamentals are tolerant of failure.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from utils.logger import get_logger

logger = get_logger("yfinance")


def fetch_price_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Return EOD OHLCV as DataFrame[date, open, high, low, close, adj_close, volume]."""
    hist = yf.Ticker(ticker).history(period=period, auto_adjust=False, raise_errors=False)
    if hist is None or hist.empty:
        return pd.DataFrame()
    hist = hist.reset_index()
    adj = hist["Adj Close"] if "Adj Close" in hist.columns else hist["Close"]
    out = pd.DataFrame({
        "date": pd.to_datetime(hist["Date"]).dt.date,
        "open": hist["Open"].astype(float),
        "high": hist["High"].astype(float),
        "low": hist["Low"].astype(float),
        "close": hist["Close"].astype(float),
        "adj_close": adj.astype(float),
        "volume": hist["Volume"].fillna(0).astype("int64"),
    })
    return out.dropna(subset=["close"]).reset_index(drop=True)


def fetch_fundamentals(ticker: str) -> dict:
    """Best-effort fundamentals snapshot. Returns dict of metrics (values may be None)."""
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as e:  # noqa: BLE001 - Yahoo .info is flaky; degrade gracefully
        logger.warning(f"{ticker}: fundamentals fetch failed ({e})")
        info = {}
    return {
        "pe": info.get("trailingPE"),
        "pb": info.get("priceToBook"),
        "peg": info.get("pegRatio") or info.get("trailingPegRatio"),
        "roe": info.get("returnOnEquity"),
        "debt_equity": info.get("debtToEquity"),
        "eps": info.get("trailingEps"),
        "div_yield": info.get("dividendYield"),
        "market_cap": info.get("marketCap"),
        "sector": info.get("sector"),
    }
