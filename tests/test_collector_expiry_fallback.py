"""
Collector expiry-fallback regression test
───────────────────────────────────────────
Guards get_option_symbols_for_today() against guessing a hardcoded weekday
when get_nearest_expiry() can't resolve an expiry.

The bug being pinned: when both the live TrueData REST lookup and the DB
fallback inside get_nearest_expiry() fail (returning None), the collector
fell back to hardcoding "next Tuesday" - the exact hardcoded-weekday failure
mode CLAUDE.md documents an incident for (NIFTY's weekly expiry day has
moved before, and individual weeks can be holiday-shifted). Guessing wrong
means subscribing to the wrong week's, or an already-expired, contract.

Run:
  python tests/test_collector_expiry_fallback.py
  # or, if pytest is installed:
  pytest tests/test_collector_expiry_fallback.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date

import backtest.option_resolver as option_resolver
from scripts.collect_ticks import get_option_symbols_for_today


def test_no_expiry_available_returns_empty_instead_of_guessing():
    option_resolver.get_nearest_expiry = lambda ref_date: None

    symbols = get_option_symbols_for_today(22500.0)

    assert symbols == [], (
        f"expected an empty list when expiry can't be resolved, got "
        f"{len(symbols)} symbols - looks like it's guessing a weekday again"
    )
    print("  ok: returns [] instead of guessing a weekday when expiry resolution fails")


def test_normal_expiry_still_builds_the_full_strike_range():
    option_resolver.get_nearest_expiry = lambda ref_date: date(2026, 3, 24)

    symbols = get_option_symbols_for_today(22500.0)

    assert len(symbols) > 0, "expected symbols when expiry resolves normally"
    assert all(s.startswith("NIFTY260324") for s in symbols), (
        f"expected all symbols to use the resolved expiry code, got {symbols[:2]}"
    )
    assert any(s.endswith("22500CE") for s in symbols), "expected an ATM call in the range"
    print(f"  ok: normal path still builds {len(symbols)} symbols around ATM")


if __name__ == "__main__":
    failures = 0
    for fn in (
        test_no_expiry_available_returns_empty_instead_of_guessing,
        test_normal_expiry_still_builds_the_full_strike_range,
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
