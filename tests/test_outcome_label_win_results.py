"""
Outcome-model label regression test
──────────────────────────────────────
Guards build_label() against labeling a losing TIMEOUT/RL_EXIT trade as a
win.

The bug being pinned: WIN_RESULTS included "TIMEOUT" and "RL_EXIT", and
build_label() checked membership in that set BEFORE checking pnl, so any
trade with one of those exit reasons was labeled WIN=1 regardless of its
actual P&L. Tracing the backtest engine: TIMEOUT (tick_replay_backtest.py)
fires purely on bars_held >= MAX_HOLD_BARS after already failing the
SL/target checks - the exit price can be anywhere between SL and target,
including underwater. RL_EXIT fires whenever the RL agent's policy picks
"EXIT" at the current premium, with no profit floor. This corrupted
training labels for every per-strategy outcome model.

Run:
  python tests/test_outcome_label_win_results.py
  # or, if pytest is installed:
  pytest tests/test_outcome_label_win_results.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from scripts.train_outcome_models import build_label, WIN_RESULTS


def _row(result: str, pnl: float) -> pd.Series:
    return pd.Series({"result": result, "pnl": pnl})


def test_losing_timeout_is_labeled_a_loss():
    label = build_label(_row("TIMEOUT", pnl=-450.0))
    assert label == 0, (
        f"expected a losing TIMEOUT trade (pnl=-450) to be labeled LOSS, "
        f"got {label} - TIMEOUT is being treated as an unconditional win again"
    )
    print("  ok: a losing TIMEOUT trade is labeled LOSS")


def test_winning_timeout_is_still_a_win():
    label = build_label(_row("TIMEOUT", pnl=200.0))
    assert label == 1, f"expected a profitable TIMEOUT trade to be labeled WIN, got {label}"
    print("  ok: a profitable TIMEOUT trade is still labeled WIN")


def test_losing_rl_exit_is_labeled_a_loss():
    label = build_label(_row("RL_EXIT", pnl=-120.0))
    assert label == 0, (
        f"expected a losing RL_EXIT trade (pnl=-120) to be labeled LOSS, "
        f"got {label} - RL_EXIT is being treated as an unconditional win again"
    )
    print("  ok: a losing RL_EXIT trade is labeled LOSS")


def test_target_and_trailing_sl_remain_unconditional_wins():
    # These are profitable by construction even if pnl happens to be
    # missing/NaN in a given row - they should not require the pnl check.
    assert build_label(_row("TARGET", pnl=float("nan"))) == 1
    assert build_label(_row("TRAILING_SL", pnl=float("nan"))) == 1
    print("  ok: TARGET and TRAILING_SL are still unconditional wins")


def test_win_results_no_longer_includes_ambiguous_reasons():
    assert "TIMEOUT" not in WIN_RESULTS, "TIMEOUT must not be an unconditional win"
    assert "RL_EXIT" not in WIN_RESULTS, "RL_EXIT must not be an unconditional win"
    assert "EOD_CLOSE" not in WIN_RESULTS, "EOD_CLOSE must not be an unconditional win"
    print(f"  ok: WIN_RESULTS = {WIN_RESULTS}")


if __name__ == "__main__":
    failures = 0
    for fn in (
        test_losing_timeout_is_labeled_a_loss,
        test_winning_timeout_is_still_a_win,
        test_losing_rl_exit_is_labeled_a_loss,
        test_target_and_trailing_sl_remain_unconditional_wins,
        test_win_results_no_longer_includes_ambiguous_reasons,
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
