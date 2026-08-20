"""
weekly_trend_slope buffer regression test
────────────────────────────────────────────
Guards compute_all_macro_indicators()'s weekly_trend_slope against being
structurally NaN at inference time.

The bug being pinned: weekly_trend_slope = close.diff(300)/close.shift(300)
needs 301 rows for the LAST row to be non-NaN. Every live/backtest call
site feeds this function a buffer capped at exactly 300 rows (14 call
sites across the codebase all use LIMIT 300 / .tail(300)), so the one row
that actually matters at scoring time - the latest bar - was ALWAYS NaN,
silently hitting XGBoost's untrained missing-value routing on every single
live/backtest prediction, even though training saw real values for this
feature on the vast majority of its (much longer) historical dataset.

The fix shrinks the lookback window when the input is short instead of
requiring every caller's buffer size to change in lockstep.

Run:
  python tests/test_weekly_trend_slope_buffer.py
  # or, if pytest is installed:
  pytest tests/test_weekly_trend_slope_buffer.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from features.indicators import compute_all_macro_indicators


def _synthetic_candles(n: int, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 22000 + np.cumsum(rng.normal(0, 5, n))
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-03-24 09:15", periods=n, freq="1min"),
        "open": close, "high": close + 5, "low": close - 5, "close": close,
        "volume": rng.integers(100, 1000, n), "vwap": close, "oi": 0,
    })


def test_exactly_300_rows_no_longer_nan_at_the_last_row():
    """The exact reported scenario: every live/backtest buffer caps at 300."""
    out = compute_all_macro_indicators(_synthetic_candles(300))
    last = out.iloc[-1]["weekly_trend_slope"]
    assert pd.notna(last), (
        "weekly_trend_slope is NaN at the last row of a 300-row buffer - "
        "this is the exact bug: every live/backtest caller uses a 300-row "
        "buffer, so this feature was always missing at scoring time"
    )
    print(f"  ok: weekly_trend_slope = {last:.6f} at exactly 300 rows (was NaN)")


def test_301_plus_rows_unaffected():
    """With enough history, behavior must be identical to the original
    fixed-300-bar window - the fix should only kick in when short on data."""
    out = compute_all_macro_indicators(_synthetic_candles(400, seed=2))
    manual = _synthetic_candles(400, seed=2)
    expected = (
        manual["close"].diff(300) / manual["close"].shift(300).replace(0, np.nan)
    )
    pd.testing.assert_series_equal(
        out["weekly_trend_slope"].reset_index(drop=True),
        expected.reset_index(drop=True),
        check_names=False,
    )
    print("  ok: with >=301 rows, output matches the original fixed-300-bar window exactly")


if __name__ == "__main__":
    failures = 0
    for fn in (
        test_exactly_300_rows_no_longer_nan_at_the_last_row,
        test_301_plus_rows_unaffected,
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
