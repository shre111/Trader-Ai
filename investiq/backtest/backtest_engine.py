"""
InvestIQ — backtest engine.

A monthly-rebalanced, equal-weight top-N strategy backtested against the Nifty 50.
Securities are ranked at each month-end by a point-in-time composite of the
factor/risk/momentum sub-scores (the ML probability is deliberately excluded to
avoid lookahead, since the model is trained on the full history). Produces an
equity curve and standard performance metrics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.risk_profiles import RiskLevel, get_risk_profile
from config.settings import BENCHMARK_SYMBOL, RISK_FREE_RATE
from database.db import read_sql
from features.factor_engine import _load_value_series
from strategy.scorer import score_universe
from utils.logger import get_logger

logger = get_logger("backtest")

_PERIODS_PER_YEAR = 12  # monthly rebalances


def _period_return(series: pd.Series, d0, d1):
    if series is None:
        return None
    v0 = series.asof(pd.Timestamp(d0))
    v1 = series.asof(pd.Timestamp(d1))
    if pd.isna(v0) or pd.isna(v1) or v0 == 0:
        return None
    return v1 / v0 - 1


def _metrics(eq: pd.DataFrame) -> dict:
    if eq.empty or len(eq) < 3:
        return {}
    rets = eq["strategy"].pct_change().dropna()
    years = max((eq["date"].iloc[-1] - eq["date"].iloc[0]).days / 365.25, 1e-6)
    total = eq["strategy"].iloc[-1] / eq["strategy"].iloc[0] - 1
    bench_total = eq["benchmark"].iloc[-1] / eq["benchmark"].iloc[0] - 1
    cagr = (1 + total) ** (1 / years) - 1
    bench_cagr = (1 + bench_total) ** (1 / years) - 1
    vol = rets.std() * np.sqrt(_PERIODS_PER_YEAR)
    sharpe = (cagr - RISK_FREE_RATE) / vol if vol else float("nan")
    roll_max = eq["strategy"].cummax()
    max_dd = float((eq["strategy"] / roll_max - 1).min())
    return {
        "total_return": round(total, 4), "cagr": round(cagr, 4),
        "benchmark_cagr": round(bench_cagr, 4), "alpha_cagr": round(cagr - bench_cagr, 4),
        "volatility": round(float(vol), 4), "sharpe": round(float(sharpe), 4),
        "max_drawdown": round(max_dd, 4), "n_periods": int(len(eq)),
    }


def run_backtest(risk_level: str = "balanced", top_n: int | None = None) -> dict:
    profile = get_risk_profile(RiskLevel(risk_level))
    top_n = top_n or profile.max_holdings

    feats = read_sql("SELECT * FROM features ORDER BY date")
    secs = read_sql(
        "SELECT symbol, sec_type, scheme_code FROM securities WHERE active=true"
    ).set_index("symbol")
    investable = [s for s in secs.index if secs.loc[s, "sec_type"] != "INDEX"]
    feats = feats[feats["symbol"].isin(investable)].copy()
    if feats.empty:
        return {"equity_curve": pd.DataFrame(), "metrics": {}}
    feats["date"] = pd.to_datetime(feats["date"])

    bench = _load_value_series(BENCHMARK_SYMBOL, "INDEX", None)
    if bench is None or bench.empty:
        return {"equity_curve": pd.DataFrame(), "metrics": {}}

    cache: dict = {}

    def vseries(sym):
        if sym not in cache:
            s = secs.loc[sym]
            cache[sym] = _load_value_series(sym, s["sec_type"], s["scheme_code"])
        return cache[sym]

    # Clean monthly rebalance schedule from the benchmark's month-end trading days,
    # restricted to the range where features exist.
    month_ends = bench.resample("ME").last().dropna().index
    fmin = feats["date"].min()
    schedule = [d.date() for d in month_ends if d >= fmin]
    if len(schedule) < 3:
        return {"equity_curve": pd.DataFrame(), "metrics": {}}

    equity = [{"date": schedule[0], "strategy": 1.0, "benchmark": 1.0}]
    val = bval = 1.0

    for d0, d1 in zip(schedule[:-1], schedule[1:]):
        # As-of features: each symbol's most recent row on/before the rebalance date.
        snap = feats[feats["date"] <= pd.Timestamp(d0)]
        if not snap.empty:
            asof = snap.sort_values("date").groupby("symbol").last().reset_index()
        else:
            asof = snap
        if len(asof) >= 3:
            scored = score_universe(asof, np.full(len(asof), 0.5))  # neutral ML → no lookahead
            scored["score"] = scored[["factor_score", "risk_score", "momentum_score"]].mean(axis=1)
            picks = scored.sort_values("score", ascending=False).head(top_n)["symbol"]
            rets = [r for r in (_period_return(vseries(s), d0, d1) for s in picks) if r is not None]
            port_ret = float(np.mean(rets)) if rets else 0.0
        else:
            port_ret = 0.0
        bench_ret = _period_return(bench, d0, d1) or 0.0
        val *= 1 + port_ret
        bval *= 1 + bench_ret
        equity.append({"date": d1, "strategy": val, "benchmark": bval})

    eq = pd.DataFrame(equity)
    metrics = _metrics(eq)
    logger.info(f"Backtest ({risk_level}) {metrics}")
    return {"equity_curve": eq, "metrics": metrics}
