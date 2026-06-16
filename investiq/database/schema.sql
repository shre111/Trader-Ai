-- ============================================================================
-- InvestIQ — TimescaleDB schema (database: investiq)
-- ============================================================================
-- Daily/EOD investing data. Time-series tables are hypertables on the DATE
-- column. Initialize via database.db.init_db().
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ── Security master (mutual funds + equities + indices) ──────────────────────
CREATE TABLE IF NOT EXISTS securities (
    id           SERIAL PRIMARY KEY,
    symbol       TEXT UNIQUE NOT NULL,   -- yfinance ticker (RELIANCE.NS) or MF scheme code
    name         TEXT NOT NULL,
    sec_type     TEXT NOT NULL,          -- EQUITY | MF | ETF | INDEX
    category     TEXT,                   -- e.g. Flexi Cap / Large Cap / IT
    fund_house   TEXT,                   -- for mutual funds
    isin         TEXT,
    benchmark    TEXT,                   -- benchmark symbol for alpha/beta
    scheme_code  TEXT,                   -- api.mfapi.in scheme code (MF only)
    active       BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_securities_type ON securities (sec_type, active);

-- ── Mutual fund NAV history ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS nav_history (
    date         DATE NOT NULL,
    scheme_code  TEXT NOT NULL,
    nav          DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (date, scheme_code)
);
SELECT create_hypertable('nav_history', 'date',
    chunk_time_interval => INTERVAL '90 days', if_not_exists => TRUE);

-- ── Equity / index EOD price history ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS price_history (
    date       DATE NOT NULL,
    symbol     TEXT NOT NULL,
    open       DOUBLE PRECISION,
    high       DOUBLE PRECISION,
    low        DOUBLE PRECISION,
    close      DOUBLE PRECISION NOT NULL,
    adj_close  DOUBLE PRECISION,
    volume     BIGINT,
    PRIMARY KEY (date, symbol)
);
SELECT create_hypertable('price_history', 'date',
    chunk_time_interval => INTERVAL '90 days', if_not_exists => TRUE);

-- ── Equity fundamentals (snapshots) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fundamentals (
    date         DATE NOT NULL,
    symbol       TEXT NOT NULL,
    pe           DOUBLE PRECISION,
    pb           DOUBLE PRECISION,
    peg          DOUBLE PRECISION,
    roe          DOUBLE PRECISION,
    debt_equity  DOUBLE PRECISION,
    eps          DOUBLE PRECISION,
    div_yield    DOUBLE PRECISION,
    market_cap   DOUBLE PRECISION,
    sector       TEXT,
    PRIMARY KEY (date, symbol)
);

-- ── Computed factor features (per security/date) ─────────────────────────────
CREATE TABLE IF NOT EXISTS features (
    date          DATE NOT NULL,
    symbol        TEXT NOT NULL,
    ret_1m        DOUBLE PRECISION,
    ret_3m        DOUBLE PRECISION,
    ret_6m        DOUBLE PRECISION,
    ret_1y        DOUBLE PRECISION,
    cagr_3y       DOUBLE PRECISION,
    volatility    DOUBLE PRECISION,
    downside_dev  DOUBLE PRECISION,
    sharpe        DOUBLE PRECISION,
    sortino       DOUBLE PRECISION,
    max_drawdown  DOUBLE PRECISION,
    beta          DOUBLE PRECISION,
    alpha         DOUBLE PRECISION,
    momentum_12_1 DOUBLE PRECISION,
    dist_200dma   DOUBLE PRECISION,
    dist_52w_high DOUBLE PRECISION,
    consistency   DOUBLE PRECISION,
    pe            DOUBLE PRECISION,
    pb            DOUBLE PRECISION,
    roe           DOUBLE PRECISION,
    debt_equity   DOUBLE PRECISION,
    div_yield     DOUBLE PRECISION,
    PRIMARY KEY (date, symbol)
);
SELECT create_hypertable('features', 'date',
    chunk_time_interval => INTERVAL '90 days', if_not_exists => TRUE);

-- ── Recommendations (BUY/HOLD/SELL signals) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendations (
    date           DATE NOT NULL,
    symbol         TEXT NOT NULL,
    action         TEXT NOT NULL,   -- BUY | HOLD | SELL
    final_score    DOUBLE PRECISION,
    ml_prob        DOUBLE PRECISION,
    factor_score   DOUBLE PRECISION,
    risk_score     DOUBLE PRECISION,
    momentum_score DOUBLE PRECISION,
    horizon_days   INT,
    rationale      TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (date, symbol)
);

-- ── Paper portfolio: transactions (append-only) ──────────────────────────────
CREATE TABLE IF NOT EXISTS portfolio_transactions (
    id      SERIAL PRIMARY KEY,
    ts      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol  TEXT NOT NULL,
    side    TEXT NOT NULL,                 -- BUY | SELL
    units   DOUBLE PRECISION NOT NULL,
    price   DOUBLE PRECISION NOT NULL,
    amount  DOUBLE PRECISION NOT NULL,
    mode    TEXT NOT NULL DEFAULT 'paper'  -- paper | live
);
CREATE INDEX IF NOT EXISTS idx_txn_symbol ON portfolio_transactions (symbol, ts DESC);

-- ── Paper portfolio: daily value snapshots (equity curve) ────────────────────
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    date         DATE NOT NULL,
    mode         TEXT NOT NULL DEFAULT 'paper',
    total_value  DOUBLE PRECISION,
    invested     DOUBLE PRECISION,
    cash         DOUBLE PRECISION,
    pnl          DOUBLE PRECISION,
    PRIMARY KEY (date, mode)
);

-- ── Model registry (versioning + metrics) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_registry (
    id          SERIAL PRIMARY KEY,
    model_name  TEXT NOT NULL,
    version     TEXT,
    trained_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    auc         DOUBLE PRECISION,
    accuracy    DOUBLE PRECISION,
    n_samples   INT,
    file_path   TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    notes       TEXT
);
