"""
RiskManager daily-loss regression test
─────────────────────────────────────────
Guards against the MAX_DAILY_LOSS name collision in config/settings.py.

The bug being pinned: MAX_DAILY_LOSS was defined twice - once as a capital
fraction (0.05 = 5%, intended for RiskManager) and again, later in the same
module, as an absolute rupee amount (-5000, intended for
broker/order_manager.py). The second definition silently won, so
RiskManager received -5000 where it expected a fraction:

    max_loss_amount = self.capital * self.max_daily_loss   # 50000 * -5000
                     = -250,000,000
    if self._daily_pnl <= -max_loss_amount:                # -daily_pnl <= 250,000,000
                                                             # always True

can_trade / validate_trade rejected every trade from a fresh RiskManager,
before a single trade was ever placed.

Run:
  python tests/test_risk_manager_daily_loss.py
  # or, if pytest is installed:
  pytest tests/test_risk_manager_daily_loss.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import MAX_DAILY_LOSS_PCT
from risk.risk_manager import RiskManager


def test_max_daily_loss_pct_is_a_small_fraction():
    assert 0 < MAX_DAILY_LOSS_PCT < 1, (
        f"expected MAX_DAILY_LOSS_PCT to be a fraction of capital (e.g. 0.05), "
        f"got {MAX_DAILY_LOSS_PCT} - looks like the name collision regressed"
    )
    print(f"  ok: MAX_DAILY_LOSS_PCT = {MAX_DAILY_LOSS_PCT} (a fraction)")


def test_fresh_risk_manager_can_trade():
    rm = RiskManager(capital=50000)
    assert rm.can_trade is True, (
        "a fresh RiskManager with no losses yet must be able to trade - "
        "got can_trade=False, meaning max_daily_loss is being read as an "
        "absolute rupee value instead of a fraction"
    )
    print("  ok: a fresh RiskManager can trade")


def test_loss_beyond_the_pct_threshold_blocks_trading():
    rm = RiskManager(capital=50000, max_daily_loss=0.05)  # 5% = Rs2500
    rm.register_entry("NIFTY26032422500CE", entry_price=100, quantity=65, direction="CALL")
    rm.register_exit("NIFTY26032422500CE", exit_price=60)  # -Rs2600 loss

    assert rm.can_trade is False, (
        f"expected trading blocked after a Rs2600 loss against a Rs2500 "
        f"(5% of 50000) daily limit, got can_trade=True (daily_pnl={rm.daily_pnl})"
    )
    print(f"  ok: can_trade=False after a {rm.daily_pnl:.0f} loss exceeds the 5% limit")


def test_loss_within_the_pct_threshold_allows_trading():
    rm = RiskManager(capital=50000, max_daily_loss=0.05)  # 5% = Rs2500
    rm.register_entry("NIFTY26032422500CE", entry_price=100, quantity=65, direction="CALL")
    rm.register_exit("NIFTY26032422500CE", exit_price=95)  # -Rs325 loss, well under Rs2500

    assert rm.can_trade is True, (
        f"expected trading still allowed after a small {rm.daily_pnl:.0f} loss "
        f"well under the Rs2500 daily limit"
    )
    print(f"  ok: can_trade=True after a small {rm.daily_pnl:.0f} loss within the 5% limit")


if __name__ == "__main__":
    failures = 0
    for fn in (
        test_max_daily_loss_pct_is_a_small_fraction,
        test_fresh_risk_manager_can_trade,
        test_loss_beyond_the_pct_threshold_blocks_trading,
        test_loss_within_the_pct_threshold_allows_trading,
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
