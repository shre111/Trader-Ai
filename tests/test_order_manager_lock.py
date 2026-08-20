"""
OrderManager lock-reentrancy regression test
───────────────────────────────────────────────
Guards against a deadlock in kill_switch() / check_sl_target().

The bug being pinned: OrderManager._lock was a plain threading.Lock()
(non-reentrant). Both check_sl_target() and kill_switch() acquire it, then
call exit_position() from inside that `with` block - and exit_position()
acquires the SAME lock again. A non-reentrant lock blocks forever on a
second acquire from the same thread, with no exception - just a permanent
hang. kill_switch() is wired to the emergency-stop route, so this froze
the "close everything now" safety feature instead of running it.

Run:
  python tests/test_order_manager_lock.py
  # or, if pytest is installed:
  pytest tests/test_order_manager_lock.py -v
"""

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("TRADE_MODE", "paper")

from datetime import datetime

from broker.order_manager import OrderManager, ManagedPosition

TIMEOUT_SECS = 5.0  # generous; a working call completes in milliseconds


def _fresh_manager_with_open_position() -> OrderManager:
    om = OrderManager()
    om._adapter.authenticate()
    om._positions.append(ManagedPosition(
        order_id="TEST-1",
        symbol="NIFTY26032422500CE",
        direction="CALL",
        strategy="test",
        entry_time=datetime.now(),
        entry_price=100.0,
        quantity=65,
        sl_price=85.0,
        target_price=150.0,
        current_price=100.0,
    ))
    return om


def _run_with_timeout(fn, timeout=TIMEOUT_SECS):
    """Run fn() in a thread; return (completed, result_or_None)."""
    result = {}

    def _target():
        result["value"] = fn()

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout)
    return (not t.is_alive()), result.get("value")


def test_kill_switch_does_not_deadlock():
    om = _fresh_manager_with_open_position()

    completed, result = _run_with_timeout(om.kill_switch)

    assert completed, (
        f"kill_switch() did not return within {TIMEOUT_SECS}s - it is "
        f"deadlocking on its own lock (calls exit_position() while still "
        f"holding _lock)"
    )
    assert result["positions_closed"] == 1, (
        f"expected kill_switch to close the 1 open position, got "
        f"positions_closed={result.get('positions_closed')}"
    )
    print(f"  ok: kill_switch() completed and closed {result['positions_closed']} position(s)")


def test_check_sl_target_does_not_deadlock_on_sl_hit():
    om = _fresh_manager_with_open_position()

    completed, _ = _run_with_timeout(
        lambda: om.check_sl_target("NIFTY26032422500CE", current_price=80.0)  # below sl_price
    )

    assert completed, (
        f"check_sl_target() did not return within {TIMEOUT_SECS}s - it is "
        f"deadlocking on its own lock (calls exit_position() while still "
        f"holding _lock)"
    )
    assert om._positions[0].status == "CLOSED", "expected the SL-hit position to be closed"
    print("  ok: check_sl_target() completed and closed the SL-hit position")


if __name__ == "__main__":
    failures = 0
    for fn in (
        test_kill_switch_does_not_deadlock,
        test_check_sl_target_does_not_deadlock_on_sl_hit,
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
