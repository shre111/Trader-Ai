"""
InvestIQ — recommendation engine.

Scores the latest factor snapshot for every investable security and maps each to a
BUY / HOLD / SELL action using the active risk profile's thresholds and gates
(max volatility, min Sharpe). Optionally honors current holdings (held names stay
HOLD while still above the hold threshold). Persists to the recommendations table,
keyed by (date, symbol, risk_level) — each profile stores its own row, since the
same security resolves to a different action under different thresholds.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from config.risk_profiles import RiskLevel, get_risk_profile
from config.settings import FEATURE_COLUMNS, LABEL_FORWARD_DAYS
from database.db import read_sql, upsert_rows
from features.factor_engine import latest_features
from models.predict import Predictor
from strategy.scorer import score_universe
from utils.logger import get_logger

logger = get_logger("recommend")


def _rationale(row) -> str:
    bits = [f"ML {row.ml_prob:.0%}"]
    if row.momentum_score >= 0.6:
        bits.append("strong momentum")
    elif row.momentum_score <= 0.4:
        bits.append("weak momentum")
    if row.risk_score >= 0.6:
        bits.append("favorable risk")
    elif row.risk_score <= 0.4:
        bits.append("elevated risk")
    if row.factor_score >= 0.6:
        bits.append("quality/value")
    return ", ".join(bits)


def generate(risk_level: str = "balanced", held=None, store: bool = True) -> pd.DataFrame:
    """Produce ranked recommendations for the given risk profile."""
    profile = get_risk_profile(RiskLevel(risk_level))
    held = set(held or [])

    lf = latest_features()
    if lf.empty:
        logger.warning("No features available — run `train` first.")
        return pd.DataFrame()

    secs = read_sql("SELECT symbol, sec_type, name, category FROM securities WHERE active=true")
    lf = lf.merge(secs, on="symbol", how="left")
    lf = lf[lf["sec_type"] != "INDEX"].reset_index(drop=True)  # index isn't directly investable

    probs = Predictor().predict_proba(lf[FEATURE_COLUMNS])
    scored = score_universe(lf, probs)

    def decide(row) -> str:
        passes_risk = (
            (pd.isna(row.volatility) or row.volatility <= profile.max_volatility)
            and (pd.isna(row.sharpe) or row.sharpe >= profile.min_sharpe)
        )
        if row.final_score >= profile.buy_threshold and passes_risk:
            return "HOLD" if row.symbol in held else "BUY"
        # A name we already own keeps its place while it stays above the hold floor —
        # that is exactly what hold_threshold documents ("keep an existing holding").
        if row.symbol in held and row.final_score >= profile.hold_threshold:
            return "HOLD"
        # Only call SELL below the explicit sell threshold. Previously anything under
        # hold_threshold was a SELL, which ignored sell_threshold entirely and flagged
        # merely-unremarkable securities as exits. The band between sell and buy is
        # neutral: not worth buying, not a reason to sell.
        if row.final_score < profile.sell_threshold:
            return "SELL"
        return "HOLD"

    scored["action"] = scored.apply(decide, axis=1)
    scored["rationale"] = scored.apply(_rationale, axis=1)
    scored = scored.sort_values("final_score", ascending=False).reset_index(drop=True)

    if store:
        rec = pd.DataFrame({
            "date": date.today(),
            "symbol": scored["symbol"],
            "risk_level": risk_level,
            "action": scored["action"],
            "final_score": scored["final_score"].round(4),
            "ml_prob": scored["ml_prob"].round(4),
            "factor_score": scored["factor_score"].round(4),
            "risk_score": scored["risk_score"].round(4),
            "momentum_score": scored["momentum_score"].round(4),
            "horizon_days": LABEL_FORWARD_DAYS,
            "rationale": scored["rationale"],
        })
        upsert_rows(rec, "recommendations", ["date", "symbol", "risk_level"], update=True)
        logger.info(f"Stored {len(rec)} recommendations ({risk_level}).")

    return scored
