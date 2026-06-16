"""
InvestIQ — Risk Profiles
────────────────────────
Investing-oriented profiles (Conservative / Balanced / Aggressive) that control
recommendation selectivity and portfolio construction:

  - BUY / HOLD / SELL score thresholds
  - Diversification (max holdings, max weight per security)
  - Target equity-vs-MF split and cash buffer
  - Risk caps (max volatility) and quality floor (min Sharpe)
  - Rebalance drift band

Usage:
  from config.risk_profiles import get_risk_profile, RiskLevel
  profile = get_risk_profile(RiskLevel.BALANCED)
  if score >= profile.buy_threshold: ...
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class RiskLevel(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass(frozen=True)
class RiskProfile:
    """Immutable parameter set tied to a risk level."""

    name: str
    level: RiskLevel

    # ── Recommendation selectivity (composite score gates) ──────────────────
    buy_threshold: float        # enter / add when score ≥ this
    hold_threshold: float       # keep an existing holding while score ≥ this
    sell_threshold: float       # exit / trim when score < this

    # ── Portfolio construction ──────────────────────────────────────────────
    max_holdings: int           # target number of positions
    max_holding_weight: float   # cap on any single security (fraction of NAV)
    target_equity_weight: float # equities vs mutual funds split
    cash_buffer: float          # fraction kept un-invested

    # ── Risk caps / quality floor ───────────────────────────────────────────
    max_volatility: float       # annualized; reject candidates above this
    min_sharpe: float           # quality floor for new buys

    # ── Rebalancing ─────────────────────────────────────────────────────────
    rebalance_band: float       # weight drift that triggers a rebalance


# ── CONSERVATIVE — capital preservation, broad diversification ────────────────
CONSERVATIVE = RiskProfile(
    name="Conservative",
    level=RiskLevel.CONSERVATIVE,
    buy_threshold=0.70,
    hold_threshold=0.50,
    sell_threshold=0.40,
    max_holdings=15,
    max_holding_weight=0.10,
    target_equity_weight=0.40,
    cash_buffer=0.10,
    max_volatility=0.18,
    min_sharpe=0.50,
    rebalance_band=0.05,
)

# ── BALANCED — default; blended growth + stability ────────────────────────────
BALANCED = RiskProfile(
    name="Balanced",
    level=RiskLevel.BALANCED,
    buy_threshold=0.62,
    hold_threshold=0.45,
    sell_threshold=0.35,
    max_holdings=12,
    max_holding_weight=0.15,
    target_equity_weight=0.60,
    cash_buffer=0.05,
    max_volatility=0.25,
    min_sharpe=0.30,
    rebalance_band=0.07,
)

# ── AGGRESSIVE — concentrated, growth-tilted ──────────────────────────────────
AGGRESSIVE = RiskProfile(
    name="Aggressive",
    level=RiskLevel.AGGRESSIVE,
    buy_threshold=0.58,
    hold_threshold=0.40,
    sell_threshold=0.30,
    max_holdings=8,
    max_holding_weight=0.25,
    target_equity_weight=0.80,
    cash_buffer=0.02,
    max_volatility=0.40,
    min_sharpe=0.00,
    rebalance_band=0.10,
)


_PROFILES: Dict[RiskLevel, RiskProfile] = {
    RiskLevel.CONSERVATIVE: CONSERVATIVE,
    RiskLevel.BALANCED: BALANCED,
    RiskLevel.AGGRESSIVE: AGGRESSIVE,
}


def get_risk_profile(level: RiskLevel) -> RiskProfile:
    """Get a risk profile by level (accepts RiskLevel or its string value)."""
    if isinstance(level, str):
        level = RiskLevel(level)
    return _PROFILES[level]


def list_profiles() -> List[dict]:
    """Return all profiles as summary dicts (for API / settings UI)."""
    return [
        {
            "level": p.level.value,
            "name": p.name,
            "buy_threshold": p.buy_threshold,
            "hold_threshold": p.hold_threshold,
            "sell_threshold": p.sell_threshold,
            "max_holdings": p.max_holdings,
            "max_holding_weight": p.max_holding_weight,
            "target_equity_weight": p.target_equity_weight,
            "max_volatility": p.max_volatility,
            "min_sharpe": p.min_sharpe,
        }
        for p in _PROFILES.values()
    ]
