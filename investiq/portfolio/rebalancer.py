"""
InvestIQ — rebalancer.

Turns the current BUY recommendations into score-weighted target positions
(capped per the risk profile, leaving a cash buffer) and executes the paper trades
to move the portfolio toward those targets. Sells first (free up cash), then buys.
"""

from __future__ import annotations

from config.risk_profiles import RiskLevel, get_risk_profile
from portfolio.paper_portfolio import PaperPortfolio
from strategy.recommendation_engine import generate
from utils.logger import get_logger

logger = get_logger("rebalance")


def rebalance(risk_level: str = "balanced", portfolio: PaperPortfolio | None = None) -> dict:
    profile = get_risk_profile(RiskLevel(risk_level))
    pf = portfolio or PaperPortfolio()

    scored = generate(risk_level=risk_level, store=False)
    if scored.empty:
        logger.warning("No recommendations — nothing to rebalance.")
        return pf.summary()

    buys = scored[scored["action"] == "BUY"].head(profile.max_holdings).copy()
    if buys.empty:
        logger.warning("No BUY candidates — holding cash.")
        return pf.summary()

    # Score-weighted target weights, capped, then renormalized.
    w = buys["final_score"] / buys["final_score"].sum()
    w = w.clip(upper=profile.max_holding_weight)
    w = w / w.sum()
    investable = pf.summary()["total_value"] * (1 - profile.cash_buffer)
    targets = dict(zip(buys["symbol"], w * investable))
    target_syms = set(targets)

    # 1) Sell everything not in the target set.
    held = pf.holdings()
    if not held.empty:
        for sym in set(held["symbol"]) - target_syms:
            pf.sell(sym, 1.0)

    # 2) Trim overweight targets down toward their target value.
    held = pf.holdings()
    cur = dict(zip(held["symbol"], held["value"])) if not held.empty else {}
    for sym, tv in targets.items():
        cv = cur.get(sym, 0.0)
        if cv - tv > 1 and cv > 0:
            pf.sell(sym, fraction=min(1.0, (cv - tv) / cv))

    # 3) Buy underweight / new targets.
    held = pf.holdings()
    cur = dict(zip(held["symbol"], held["value"])) if not held.empty else {}
    for sym, tv in targets.items():
        diff = tv - cur.get(sym, 0.0)
        if diff > 1:
            pf.buy(sym, diff)

    summary = pf.snapshot()
    logger.info(f"Rebalanced ({risk_level}): {summary['n_holdings']} holdings, "
                f"value {summary['total_value']:.0f}, cash {summary['cash']:.0f}")
    return summary
