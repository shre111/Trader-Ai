-- ============================================================================
-- Migration 001 — add risk_level to recommendations
-- ============================================================================
-- Problem: recommendations was keyed PRIMARY KEY (date, symbol), but the action
-- a security resolves to depends on the risk profile (each has different
-- buy/hold thresholds and max_volatility / min_sharpe gates). The daily refresh
-- job stores conservative, then balanced, then aggressive in turn — so with
-- update=True on (date, symbol), each profile silently overwrote the previous
-- one and only the last survived.
--
-- Fix: make risk_level part of the primary key.
--
-- Existing rows: we cannot know which profile produced them (the loop order
-- means they are *probably* aggressive, but "probably" is not a label worth
-- writing), so they are marked 'unknown' rather than guessed. They are
-- regenerated correctly on the next `main.py recommend` / daily refresh.
--
-- Safe to re-run: the ADD COLUMN is IF NOT EXISTS and the constraint swap is
-- guarded. Wrap in a transaction so a failure leaves the table untouched.
--
-- Apply with:
--   docker exec -i aitrader-timescaledb psql -U postgres -d investiq \
--     -v ON_ERROR_STOP=1 -f - < investiq/database/migrations/001_recommendations_risk_level.sql
-- ============================================================================

BEGIN;

-- 1. Add the column. DEFAULT satisfies NOT NULL for pre-existing rows.
ALTER TABLE recommendations
    ADD COLUMN IF NOT EXISTS risk_level TEXT NOT NULL DEFAULT 'unknown';

-- 2. Label pre-existing rows honestly (only those still on the default).
UPDATE recommendations SET risk_level = 'unknown' WHERE risk_level IS NULL;

-- 3. Swap the primary key to include risk_level.
ALTER TABLE recommendations DROP CONSTRAINT IF EXISTS recommendations_pkey;
ALTER TABLE recommendations ADD PRIMARY KEY (date, symbol, risk_level);

-- 4. Drop the DEFAULT — new rows must state their profile explicitly, so a
--    missing risk_level fails loudly instead of silently landing in 'unknown'.
ALTER TABLE recommendations ALTER COLUMN risk_level DROP DEFAULT;

COMMIT;
