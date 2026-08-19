"""
Option premium as-of-lookup regression tests
─────────────────────────────────────────────
Guards resolve_option_at_entry() (and the same pattern repeated across the
backtest tooling) against picking the wrong candle when resolving the
premium at a given timestamp.

The bug being pinned: the lookup used a symmetric ±1-minute window and took
the FIRST (earliest) match. Since adjacent 1-min candles are always exactly
60s apart, whenever the prior candle existed it also fell inside that window
and was picked over the candle at the requested timestamp — the typical
case, not an edge case. Worse, if the candle at the timestamp was missing
but a later one existed, the earliest-match logic could return a candle
from the FUTURE relative to the requested timestamp — a lookahead leak in
backtest fills.

The fix: an as-of lookup — most recent candle at-or-before the timestamp,
within a 1-minute tolerance.

Run:
  python tests/test_option_asof_lookup.py
  # or, if pytest is installed:
  pytest tests/test_option_asof_lookup.py -v
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import backtest.option_resolver as option_resolver
from backtest.option_resolver import (
    resolve_option_at_entry, build_option_symbol, clear_cache,
)

EXPIRY = date(2026, 3, 24)
INDEX_PRICE = 22500.0
ATM_SYMBOL = build_option_symbol(EXPIRY, 22500, "CE")


def _install_fake_read_sql(candles: pd.DataFrame):
    """Patch option_resolver.read_sql so load_option_premiums_for_day sees
    no ticks (forcing candle mode) and only the ATM symbol has candle data."""

    def _fake_read_sql(sql, params=None):
        if "tick_data" in sql:
            return pd.DataFrame(columns=["timestamp", "premium", "bid", "ask"])
        if "minute_candles" in sql:
            if params and params.get("sym") == ATM_SYMBOL:
                return candles.copy()
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "premium", "volume", "oi"])
        raise AssertionError(f"unexpected query: {sql}")

    option_resolver.read_sql = _fake_read_sql


def _setup(candles: pd.DataFrame):
    clear_cache()
    _install_fake_read_sql(candles)
    option_resolver.get_nearest_expiry = lambda ref_date: EXPIRY


def _candles(rows):
    """rows: list of (HH:MM, premium) on 2026-03-24."""
    return pd.DataFrame({
        "timestamp": [pd.Timestamp(f"2026-03-24 {t}:00") for t, _ in rows],
        "open": [p for _, p in rows],
        "high": [p for _, p in rows],
        "low": [p for _, p in rows],
        "premium": [p for _, p in rows],
        "volume": [100] * len(rows),
        "oi": [0] * len(rows),
    })


def test_exact_match_uses_the_requested_bar():
    """When the candle at ts exists, use it — not a neighbor."""
    candles = _candles([("10:14", 100.0), ("10:15", 105.0), ("10:16", 110.0)])
    _setup(candles)

    result = resolve_option_at_entry(
        INDEX_PRICE, pd.Timestamp("2026-03-24 10:15:00"), "CALL",
    )
    assert result is not None
    assert result["entry_premium"] == 105.0, (
        f"expected the 10:15 bar's own premium (105.0), got {result['entry_premium']}"
    )
    print("  ok: exact-timestamp match returns that bar's own premium")


def test_gap_falls_back_to_prior_bar_not_future_bar():
    """When the candle at ts is missing, fall back to the PRIOR bar — never
    a bar timestamped after ts (that would be a lookahead leak)."""
    # 10:16 is missing; 10:15 (past) and 10:17 (future) both exist.
    candles = _candles([("10:14", 100.0), ("10:15", 105.0), ("10:17", 999.0)])
    _setup(candles)

    result = resolve_option_at_entry(
        INDEX_PRICE, pd.Timestamp("2026-03-24 10:16:00"), "CALL",
    )
    assert result is not None
    assert result["entry_premium"] == 105.0, (
        f"expected fallback to the 10:15 (prior) bar's premium (105.0), "
        f"got {result['entry_premium']} - this would mean a future bar leaked in"
    )
    print("  ok: gap at ts falls back to the prior bar, not the future bar")


def test_adjacent_bars_pick_current_not_prior():
    """Regression for the specific reported bug: with both the prior bar and
    the current bar present (the normal, non-gap case), the current bar must
    win — not the prior one."""
    candles = _candles([(f"09:{15+i:02d}", 100.0 + i) for i in range(10)])
    _setup(candles)

    ts = pd.Timestamp("2026-03-24 09:20:00")
    result = resolve_option_at_entry(INDEX_PRICE, ts, "CALL")
    assert result is not None
    assert result["entry_premium"] == 105.0, (
        f"expected the 09:20 bar's own premium (105.0), got "
        f"{result['entry_premium']} (109:19's premium would be 104.0)"
    )
    print("  ok: with both prior and current bars present, current bar wins")


if __name__ == "__main__":
    failures = 0
    for fn in (
        test_exact_match_uses_the_requested_bar,
        test_gap_falls_back_to_prior_bar_not_future_bar,
        test_adjacent_bars_pick_current_not_prior,
    ):
        print(f"\n{fn.__name__}")
        try:
            fn()
        except AssertionError as e:
            failures += 1
            print(f"  FAIL: {str(e).splitlines()[0]}")

    print("\n" + "=" * 60)
    print("ALL PASSED" if failures == 0 else f"{failures} FAILED")
    sys.exit(1 if failures else 0)
