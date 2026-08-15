"""
Look-ahead / leakage regression tests
─────────────────────────────────────
Guards training data prep against future information leaking backward into
earlier bars.

The bug being pinned: prepare_data() used `.ffill().bfill()` on the feature
matrix. Because ffill runs first, bfill's only effect is on the LEADING NaN
block — the indicator warmup window (SMA200 needs 200 bars). Those bars were
filled from the first bar that had data, i.e. from the future. And since this
ran before walk_forward_split(), the leak crossed every fold boundary, which
inflates reported AUC and makes each retrain behave unpredictably live.

Run:
  python tests/test_no_lookahead.py
  # or, if pytest is installed:
  pytest tests/test_no_lookahead.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from models.train_model import MacroModelTrainer, walk_forward_split

WARMUP = 50  # bars of indicator warmup before sma200 has a value


def _synthetic_features(n: int = 400) -> pd.DataFrame:
    """Minute candles with a leading NaN warmup window in one feature."""
    rng = np.random.default_rng(0)
    close = 22000 + np.cumsum(rng.normal(0, 5, n))

    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-03-02 09:15", periods=n, freq="1min"),
        "close": close,
        "rsi": rng.uniform(30, 70, n),
        "atr": rng.uniform(5, 25, n),
    })

    # sma200 must VARY across bars — a constant column fills to the same value
    # forward or backward, which would hide the bug entirely.
    df["sma200"] = np.arange(n, dtype=float) * 10.0
    df.loc[: WARMUP - 1, "sma200"] = np.nan
    return df


def _trainer():
    t = MacroModelTrainer()
    t.feature_cols = ["rsi", "atr", "sma200"]
    return t


def test_warmup_rows_are_dropped_not_backfilled():
    """Leading NaN warmup must be dropped, never filled from future bars."""
    df = _synthetic_features()
    out = _trainer().prepare_data(df)

    assert len(out) <= len(df) - WARMUP, (
        f"expected >={WARMUP} warmup rows dropped, got {len(df) - len(out)} "
        f"- bfill may have back-filled them from future bars"
    )
    assert not out["sma200"].isna().any(), "surviving rows must have no NaN"
    print(f"  ok: dropped {len(df) - len(out)} warmup rows instead of back-filling")


def test_no_output_row_predates_its_own_features():
    """
    The precise check: the earliest retained bar must be at or after the first
    bar where every feature natively has a value.

    A back-fill lets bar 0 carry sma200 from bar 50, so bar 0 survives and this
    assertion trips. Forward-fill alone cannot manufacture a value for bar 0,
    so those bars are dropped and the earliest survivor is bar 50.
    """
    df = _synthetic_features()
    features = ["rsi", "atr", "sma200"]

    first_valid_pos = int(df[features].notna().all(axis=1).values.argmax())
    first_valid_ts = df["timestamp"].iloc[first_valid_pos]

    out = _trainer().prepare_data(df)
    earliest_kept = out["timestamp"].min()

    assert earliest_kept >= first_valid_ts, (
        f"row at {earliest_kept} survived, but features were only complete from "
        f"{first_valid_ts} - it was back-filled from a future bar"
    )
    print(f"  ok: earliest kept bar {earliest_kept} >= first fully-valid bar {first_valid_ts}")


def test_values_match_a_causal_fill():
    """
    Every retained value must equal what a forward-only fill would produce.
    Recomputing the expected matrix independently catches any fill direction
    change, not just bfill.
    """
    df = _synthetic_features()
    features = ["rsi", "atr", "sma200"]

    expected = df.set_index("timestamp")[features].replace(
        [np.inf, -np.inf], np.nan
    ).ffill()

    out = _trainer().prepare_data(df).set_index("timestamp")[features]
    aligned = expected.loc[out.index]

    pd.testing.assert_frame_equal(out, aligned, check_dtype=False)
    print(f"  ok: all {len(out)} retained rows match an independent forward-only fill")


def test_walk_forward_splits_do_not_overlap():
    """Train indices must always precede test indices - no shuffling."""
    df = _synthetic_features()
    df["target"] = (df["close"].shift(-15) / df["close"] - 1 > 0.001).astype(int)
    df = df.dropna(subset=["target"]).reset_index(drop=True)

    splits = walk_forward_split(df, n_splits=5)
    assert len(splits) == 5

    for i, (train, test) in enumerate(splits):
        assert train.index.max() < test.index.min(), (
            f"split {i}: train index {train.index.max()} overlaps "
            f"test index {test.index.min()}"
        )
    print(f"  ok: all {len(splits)} walk-forward splits are strictly ordered")


if __name__ == "__main__":
    failures = 0
    for fn in (
        test_warmup_rows_are_dropped_not_backfilled,
        test_no_output_row_predates_its_own_features,
        test_values_match_a_causal_fill,
        test_walk_forward_splits_do_not_overlap,
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
