"""
InvestIQ — composite scorer.

Blends the ML outperformance probability with three cross-sectional sub-scores
(computed as percentile ranks across the universe at one point in time):

  factor    — quality/value: ROE, low PE/PB, low debt, consistency vs benchmark
  risk      — Sharpe, Sortino, low volatility, shallow max drawdown
  momentum  — 6m/1y returns, 12-1 momentum, proximity to 52-week high

  final_score = 0.45*ML + 0.25*factor + 0.15*risk + 0.15*momentum   (all in [0,1])

Cross-sectional ranking makes the sub-scores comparable across securities, which
is what a recommendation list needs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import WEIGHT_FACTOR, WEIGHT_ML, WEIGHT_MOMENTUM, WEIGHT_RISK


def _pct(s: pd.Series) -> pd.Series:
    """Percentile rank in [0,1] (NaN stays NaN)."""
    return s.rank(pct=True)


def score_universe(feat: pd.DataFrame, ml_probs) -> pd.DataFrame:
    """Add ml_prob, factor/risk/momentum sub-scores and final_score to a feature frame."""
    df = feat.copy().reset_index(drop=True)
    df["ml_prob"] = np.asarray(ml_probs, dtype=float)

    factor = pd.DataFrame({
        "roe": _pct(df["roe"]),
        "low_pe": 1 - _pct(df["pe"]),
        "low_pb": 1 - _pct(df["pb"]),
        "low_de": 1 - _pct(df["debt_equity"]),
        "consistency": _pct(df["consistency"]),
    })
    risk = pd.DataFrame({
        "sharpe": _pct(df["sharpe"]),
        "sortino": _pct(df["sortino"]),
        "low_vol": 1 - _pct(df["volatility"]),
        "shallow_dd": _pct(df["max_drawdown"]),  # less negative → higher percentile
    })
    momentum = pd.DataFrame({
        "ret_6m": _pct(df["ret_6m"]),
        "ret_1y": _pct(df["ret_1y"]),
        "mom_12_1": _pct(df["momentum_12_1"]),
        "near_high": _pct(df["dist_52w_high"]),  # closer to 0 → higher percentile
    })

    df["factor_score"] = factor.mean(axis=1, skipna=True).fillna(0.5)
    df["risk_score"] = risk.mean(axis=1, skipna=True).fillna(0.5)
    df["momentum_score"] = momentum.mean(axis=1, skipna=True).fillna(0.5)

    df["final_score"] = (
        WEIGHT_ML * df["ml_prob"]
        + WEIGHT_FACTOR * df["factor_score"]
        + WEIGHT_RISK * df["risk_score"]
        + WEIGHT_MOMENTUM * df["momentum_score"]
    )
    return df
