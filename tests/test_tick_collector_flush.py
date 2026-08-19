"""
TickCollector.flush() regression tests
────────────────────────────────────────
Guards against silently losing buffered ticks on a failed DB write.

The bug being pinned: self._buffer.clear() sat after the try/except at the
same indent level, so it ran unconditionally - even when write_df() raised.
A transient DB error (dropped connection, etc.) during a 200-tick flush
silently dropped all 200 ticks with no retry.

Run:
  python tests/test_tick_collector_flush.py
  # or, if pytest is installed:
  pytest tests/test_tick_collector_flush.py -v
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data.tick_collector as tick_collector_module
from data.tick_collector import TickCollector


def _make_ticks(n):
    return [
        {"timestamp": datetime.now(), "symbol": "NIFTY-I", "price": 22000.0 + i, "volume": 10}
        for i in range(n)
    ]


def test_failed_write_keeps_the_buffer():
    tick_collector_module.write_df = lambda df, table: (_ for _ in ()).throw(RuntimeError("db down"))

    tc = TickCollector(buffer_size=1000)
    for t in _make_ticks(5):
        tc.on_tick(t)
    assert len(tc.get_buffer()) == 5

    tc.flush()
    assert len(tc.get_buffer()) == 5, (
        f"expected all 5 ticks retained after a failed write, got {len(tc.get_buffer())} "
        f"- flush() is dropping ticks on DB failure"
    )
    print("  ok: buffer retained after a failed write_df()")


def test_failed_then_succeeding_flush_does_not_lose_ticks():
    """The realistic retry scenario: a transient failure followed by a
    successful flush must persist everything, not just the latest batch."""
    calls = {"n": 0, "written": None}

    def _flaky_write(df, table):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient db error")
        calls["written"] = len(df)

    tick_collector_module.write_df = _flaky_write

    tc = TickCollector(buffer_size=1000)
    for t in _make_ticks(3):
        tc.on_tick(t)
    tc.flush()  # fails, buffer must survive
    assert len(tc.get_buffer()) == 3

    for t in _make_ticks(2):
        tc.on_tick(t)
    tc.flush()  # succeeds now

    assert calls["written"] == 5, (
        f"expected the retried flush to write all 5 buffered ticks (3 from "
        f"the failed attempt + 2 new), got {calls['written']}"
    )
    assert len(tc.get_buffer()) == 0, "buffer must be empty after a successful flush"
    print("  ok: retried flush after a transient failure writes every buffered tick")


def test_successful_write_clears_the_buffer():
    tick_collector_module.write_df = lambda df, table: None

    tc = TickCollector(buffer_size=1000)
    for t in _make_ticks(4):
        tc.on_tick(t)
    tc.flush()
    assert len(tc.get_buffer()) == 0, "buffer must be cleared after a successful write"
    print("  ok: buffer cleared after a successful write_df()")


if __name__ == "__main__":
    failures = 0
    for fn in (
        test_failed_write_keeps_the_buffer,
        test_failed_then_succeeding_flush_does_not_lose_ticks,
        test_successful_write_clears_the_buffer,
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
