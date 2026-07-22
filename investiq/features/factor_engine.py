"""
InvestIQ — factor engine.

Turns a security's daily price/NAV history into the 21-feature factor vector
(see config.settings.FEATURE_COLUMNS): trailing returns, risk (volatility,
downside deviation, Sharpe, Sortino, max drawdown, beta, alpha), momentum/trend,
consistency vs benchmark, and equity fundamentals.

All rolling features are computed point-in-time (using only data up to each date),
then sampled at ~monthly cadence on real trading dates for training, always
including the latest date for live recommendations.

Note: free data only provides *current* fundamentals, so the latest snapshot is
broadcast across a symbol's history — a documented simplification of this design.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import (
    FEATURE_COLUMNS,
    MAX_FEATURE_STALENESS_DAYS,
    RISK_FREE_RATE,
    TRADING_DAYS_PER_YEAR,
)
from database.db import read_sql, upsert_rows
from utils.logger import get_logger

logger = get_logger("factor_engine")

RF = RISK_FREE_RATE
TD = TRADING_DAYS_PER_YEAR
_FUND_COLS = ["pe", "pb", "roe", "debt_equity", "div_yield"]


def _load_value_series(symbol: str, sec_type: str, scheme_code) -> pd.Series | None:
    """
    Load a daily value series on a consistent TOTAL-RETURN basis.

    Mutual funds: Growth-plan NAV already reinvests income, so it is total return.
    Equities/indices: use `adj_close` (dividend-adjusted), falling back to `close`
    only where the adjusted value is missing.

    Using raw `close` here compared funds on a total-return basis against equities on
    a price-only basis — a systematic bias against dividend payers in what is a purely
    cross-sectional ranking. Over the stored window COALINDIA returned 318% on a total
    -return basis but only 176% on price alone; ONGC 169% vs 97%. Those gaps flow
    straight into ret_*/cagr/sharpe/alpha and therefore into the factor ranks.
    """
    if sec_type == "MF":
        df = read_sql(
            "SELECT date, nav AS val FROM nav_history WHERE scheme_code=:c ORDER BY date",
            {"c": scheme_code},
        )
    else:
        df = read_sql(
            "SELECT date, COALESCE(adj_close, close) AS val FROM price_history "
            "WHERE symbol=:s ORDER BY date",
            {"s": symbol},
        )
    if df.empty:
        return None
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["val"].astype(float)


def _rolling_features(val: pd.Series, bench: pd.Series) -> pd.DataFrame:
    """Compute all price-derived rolling features (point-in-time) for a series."""
    b = bench.reindex(val.index).ffill()
    r = val.pct_change()
    rb = b.pct_change()
    rf_d = RF / TD

    out = pd.DataFrame(index=val.index)
    out["ret_1m"] = val / val.shift(21) - 1
    out["ret_3m"] = val / val.shift(63) - 1
    out["ret_6m"] = val / val.shift(126) - 1
    out["ret_1y"] = val / val.shift(252) - 1
    out["cagr_3y"] = (val / val.shift(756)) ** (1 / 3) - 1

    vol = r.rolling(252).std()
    out["volatility"] = vol * np.sqrt(TD)
    downside = r.where(r < 0, 0.0)
    out["downside_dev"] = downside.rolling(252).std() * np.sqrt(TD)
    mean_r = r.rolling(252).mean()
    out["sharpe"] = (mean_r * TD - RF) / (vol * np.sqrt(TD))
    out["sortino"] = (mean_r * TD - RF) / out["downside_dev"]

    roll_max = val.rolling(252, min_periods=20).max()
    out["max_drawdown"] = (val / roll_max - 1).rolling(252, min_periods=20).min()

    cov = r.rolling(252).cov(rb)
    var = rb.rolling(252).var()
    out["beta"] = cov / var
    out["alpha"] = (mean_r - rf_d - out["beta"] * (rb.rolling(252).mean() - rf_d)) * TD

    out["momentum_12_1"] = val.shift(21) / val.shift(252) - 1
    out["dist_200dma"] = val / val.rolling(200).mean() - 1
    out["dist_52w_high"] = val / val.rolling(252, min_periods=20).max() - 1

    sec_3m = val / val.shift(63) - 1
    ben_3m = b / b.shift(63) - 1
    out["consistency"] = (sec_3m > ben_3m).astype(float).rolling(252).mean()

    return out.replace([np.inf, -np.inf], np.nan)


def _load_fundamentals() -> pd.DataFrame:
    """Latest fundamentals snapshot per symbol, indexed by symbol."""
    f = read_sql(f"SELECT symbol, {', '.join(_FUND_COLS)}, date FROM fundamentals")
    if f.empty:
        return pd.DataFrame(columns=_FUND_COLS)
    return f.sort_values("date").groupby("symbol").last()[_FUND_COLS]


def build_features(symbols: list | None = None, every_n: int = 21, store: bool = True) -> pd.DataFrame:
    """
    Compute the factor vector for each active security at ~monthly cadence (plus the
    latest date), returning a tidy DataFrame [date, symbol, <FEATURE_COLUMNS>].
    Stores into the `features` hypertable when store=True.
    """
    secs = read_sql(
        "SELECT symbol, sec_type, scheme_code, benchmark FROM securities WHERE active=true"
    )
    if symbols:
        secs = secs[secs["symbol"].isin(symbols)]
    funds = _load_fundamentals()

    bench_cache: dict = {}
    frames = []
    for _, s in secs.iterrows():
        val = _load_value_series(s["symbol"], s["sec_type"], s["scheme_code"])
        if val is None or len(val) < 260:
            continue
        bsym = s["benchmark"]
        if bsym not in bench_cache:
            bench_cache[bsym] = _load_value_series(bsym, "INDEX", None)
        bench = bench_cache.get(bsym)
        if bench is None or bench.empty:
            logger.warning(f"  {s['symbol']}: benchmark {bsym} missing — skipped")
            continue

        feats = _rolling_features(val, bench)
        sampled = feats.iloc[::every_n]
        if len(feats) and (sampled.empty or sampled.index[-1] != feats.index[-1]):
            sampled = pd.concat([sampled, feats.iloc[[-1]]])  # always include latest
        sampled = sampled.dropna(subset=["ret_6m", "volatility", "sharpe"])
        if sampled.empty:
            continue

        sampled = sampled.copy()
        sampled["symbol"] = s["symbol"]
        for col in _FUND_COLS:
            sampled[col] = funds.loc[s["symbol"], col] if s["symbol"] in funds.index else np.nan
        frames.append(sampled.reset_index().rename(columns={"index": "date"}))

    if not frames:
        logger.warning("No features computed (insufficient data).")
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.date
    out = out[["date", "symbol"] + FEATURE_COLUMNS]

    if store:
        n = upsert_rows(out, "features", ["date", "symbol"], update=True)
        logger.info(f"Stored {n} feature rows for {out['symbol'].nunique()} securities.")
    return out


def latest_features(symbols: list | None = None,
                    max_staleness_days: int = MAX_FEATURE_STALENESS_DAYS) -> pd.DataFrame:
    """
    Most recent feature row per symbol from the `features` table, excluding symbols
    whose data has gone stale.

    The max(date) join is per-symbol, so a security that stopped updating still
    returns its last-ever row. Downstream scoring is cross-sectional (percentile
    ranks across the universe), which silently compares those stale factors against
    current ones — a fund last seen in 2014 could be ranked, and recommended, today.
    Drop anything trailing the freshest row by more than `max_staleness_days`.

    Pass max_staleness_days=0 to disable the guard (e.g. historical analysis).
    """
    df = read_sql(
        """
        SELECT f.* FROM features f
        JOIN (SELECT symbol, max(date) d FROM features GROUP BY symbol) m
          ON f.symbol = m.symbol AND f.date = m.d
        """
    )
    if symbols and not df.empty:
        df = df[df["symbol"].isin(symbols)]
    if df.empty or not max_staleness_days:
        return df

    dates = pd.to_datetime(df["date"])
    cutoff = dates.max() - pd.Timedelta(days=max_staleness_days)
    stale = df[dates < cutoff]
    if not stale.empty:
        for _, r in stale.iterrows():
            logger.warning(
                f"  {r['symbol']}: features last updated {r['date']} "
                f"(> {max_staleness_days}d stale) — excluded from scoring"
            )
    return df[dates >= cutoff].reset_index(drop=True)
