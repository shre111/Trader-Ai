"""
InvestIQ — central configuration.

All constants are environment-overridable via a `.env` file (loaded once here).
Mirrors the reference project's config pattern but for the investing domain.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ── Database (TimescaleDB; shared Docker container on host port 5440) ─────────
# NOTE: 5432/5433 are taken by native Postgres on this host — InvestIQ uses 5440
# and its own database `investiq` (isolated from the trading `trading` DB).
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5440")
DB_NAME = os.getenv("INVESTIQ_DB_NAME", "investiq")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    if DB_PASSWORD
    else f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── Market / domain constants ─────────────────────────────────────────────────
BENCHMARK_SYMBOL = os.getenv("BENCHMARK_SYMBOL", "^NSEI")     # Nifty 50 index
RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.065"))  # annual, for Sharpe/alpha
TRADING_DAYS_PER_YEAR = 252

# ── Feature set — the factor vector computed per security/date ────────────────
FEATURE_COLUMNS = [
    # Returns
    "ret_1m", "ret_3m", "ret_6m", "ret_1y", "cagr_3y",
    # Risk
    "volatility", "downside_dev", "sharpe", "sortino", "max_drawdown",
    "beta", "alpha",
    # Momentum / trend
    "momentum_12_1", "dist_200dma", "dist_52w_high", "consistency",
    # Fundamentals (equities; 0 / median-filled for mutual funds)
    "pe", "pb", "roe", "debt_equity", "div_yield",
]

# ── Supervised label — "did it outperform the benchmark going forward?" ───────
LABEL_FORWARD_DAYS = int(os.getenv("LABEL_FORWARD_DAYS", "126"))      # ~6 months
LABEL_OUTPERFORM_MARGIN = float(os.getenv("LABEL_OUTPERFORM_MARGIN", "0.0"))

# ── Composite recommendation score weights (sum ≈ 1.0) ────────────────────────
WEIGHT_ML = float(os.getenv("WEIGHT_ML", "0.45"))
WEIGHT_FACTOR = float(os.getenv("WEIGHT_FACTOR", "0.25"))
WEIGHT_RISK = float(os.getenv("WEIGHT_RISK", "0.15"))
WEIGHT_MOMENTUM = float(os.getenv("WEIGHT_MOMENTUM", "0.15"))

# ── Paper portfolio ───────────────────────────────────────────────────────────
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "100000"))

# ── Model persistence ─────────────────────────────────────────────────────────
_MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(_MODULE_ROOT, "models", "saved"))
MODEL_PATH = os.path.join(MODEL_DIR, "outperformance_model.pkl")

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
