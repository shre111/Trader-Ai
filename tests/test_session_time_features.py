"""
Session-time feature regression test
─────────────────────────────────────
Guards the session-time block in compute_all_macro_indicators() against a
UTC/IST offset bug: minutes_since_open was computed as

    ts.dt.hour * 60 + ts.dt.minute - 225

which is only correct if ts is true UTC (09:15 IST = 03:45 UTC = minute
225). But DB timestamps in this project are IST wall-clock values stored
mislabeled as +00:00 (see CLAUDE.md - confirmed by tracing collect_ticks.py,
which writes naive datetime.now() with no tz conversion, and independently
by scripts/run_premium_backtest_v2.py's own minutes_since_open, which
correctly uses "- 555"). So ts.dt.hour/minute are already IST, and the
correct offset is 555 (9*60+15), not 225.

Under the bug, the computed value ranged ~330-705 across every session
instead of 0-375: is_first_hour (<=60) was always 0, and is_last_hour
(>=315) was always 1, for every single row, in both training and live
scoring.

Run:
  python tests/test_session_time_features.py
  # or, if pytest is installed:
  pytest tests/test_session_time_features.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from features.indicators import compute_all_macro_indicators


def _synthetic_session(n: int = 400) -> pd.DataFrame:
    """One trading day of 1-min candles starting at 09:15 IST (naive, matching
    how this project's DB timestamps actually arrive)."""
    rng = np.random.default_rng(0)
    close = 22000 + np.cumsum(rng.normal(0, 5, n))
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-03-24 09:15", periods=n, freq="1min"),
        "open": close, "high": close + 5, "low": close - 5, "close": close,
        "volume": rng.integers(100, 1000, n), "vwap": close, "oi": 0,
    })


def test_minutes_since_open_is_zero_at_market_open():
    out = compute_all_macro_indicators(_synthetic_session())
    first = out.iloc[0]
    assert first["minutes_since_open"] == 0, (
        f"expected 0 minutes since open at 09:15, got {first['minutes_since_open']} "
        f"- looks like the UTC/IST offset regressed"
    )
    print("  ok: minutes_since_open == 0 at 09:15 (market open)")


def test_is_first_hour_and_is_last_hour_are_not_constant():
    """The exact bug signature: under the old -225 offset, is_first_hour was
    always 0 and is_last_hour was always 1 for every row, all session long."""
    out = compute_all_macro_indicators(_synthetic_session())

    assert out["is_first_hour"].nunique() > 1, (
        "is_first_hour never varies across the session - matches the old "
        "always-0 bug signature"
    )
    assert out["is_last_hour"].nunique() > 1, (
        "is_last_hour never varies across the session - matches the old "
        "always-1 bug signature"
    )
    assert bool(out.iloc[0]["is_first_hour"]) is True, "09:15 should be in the first hour"
    assert bool(out.iloc[0]["is_last_hour"]) is False, "09:15 should not be in the last hour"
    print("  ok: is_first_hour/is_last_hour vary correctly across the session")


def test_session_progress_stays_in_expected_range():
    out = compute_all_macro_indicators(_synthetic_session())
    # A full 375-min session should land close to 1.0 near the end, not ~1.9
    # (the old bug's ~330min head start pushed this well past 1.0 all day).
    near_close = out[out["timestamp"].dt.strftime("%H:%M") == "15:29"]
    assert not near_close.empty
    progress = float(near_close.iloc[0]["session_progress"])
    assert 0.95 <= progress <= 1.05, (
        f"expected session_progress near 1.0 at 15:29, got {progress}"
    )
    print(f"  ok: session_progress at 15:29 = {progress:.3f} (expected ~1.0)")


if __name__ == "__main__":
    failures = 0
    for fn in (
        test_minutes_since_open_is_zero_at_market_open,
        test_is_first_hour_and_is_last_hour_are_not_constant,
        test_session_progress_stays_in_expected_range,
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
