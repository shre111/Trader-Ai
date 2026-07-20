"""
InvestIQ — outperformance model training.

Target: "Will this security beat its benchmark over the next ~6 months?" Labels
come from forward returns (security vs benchmark) at each feature date. Trained
with walk-forward (time-series) validation and an XGBoost classifier, mirroring
the reference project's training harness. Persists the model + metrics, keeps a
timestamped backup, and records a model_registry row.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit

from config.settings import (
    FEATURE_COLUMNS,
    LABEL_FORWARD_DAYS,
    LABEL_OUTPERFORM_MARGIN,
    MODEL_DIR,
    MODEL_PATH,
)
from database.db import read_sql, execute_sql
from features.factor_engine import _load_value_series
from utils.logger import get_logger

logger = get_logger("train_model")


def attach_labels(feat: pd.DataFrame, forward: int = LABEL_FORWARD_DAYS,
                  margin: float = LABEL_OUTPERFORM_MARGIN) -> pd.DataFrame:
    """Attach a binary `target` = 1 if forward return beats the benchmark by `margin`."""
    secs = read_sql(
        "SELECT symbol, sec_type, scheme_code, benchmark FROM securities WHERE active=true"
    ).set_index("symbol")
    feat = feat.copy()
    feat["target"] = np.nan
    bench_cache: dict = {}

    for sym, grp in feat.groupby("symbol"):
        if sym not in secs.index:
            continue
        s = secs.loc[sym]
        val = _load_value_series(sym, s["sec_type"], s["scheme_code"])
        if val is None:
            continue
        bsym = s["benchmark"]
        if bsym not in bench_cache:
            bench_cache[bsym] = _load_value_series(bsym, "INDEX", None)
        bench = bench_cache[bsym]
        if bench is None or bench.empty:
            continue

        valr = val.values
        pos = {d: i for i, d in enumerate(val.index)}
        benr = bench.reindex(val.index).ffill().values

        for idx, row in grp.iterrows():
            i = pos.get(pd.Timestamp(row["date"]))
            if i is None or i + forward >= len(valr):
                continue
            b0, b1 = benr[i], benr[i + forward]
            # The label is "did it BEAT THE BENCHMARK", so it is only defined where the
            # benchmark actually covers both ends of the forward window. Leave `target`
            # NaN otherwise — train() drops those rows.
            #
            # Previously b1 was unguarded: a NaN there made ben_fwd NaN, and the
            # comparison `NaN > margin` is False, so the row was silently labelled 0
            # (underperform) — a +25% winner recorded as a loss. A NaN b0 was just as
            # bad: `b0 and not isnan(b0)` is False for NaN (NaN is truthy), so the
            # benchmark was treated as flat 0%, quietly turning the label into the much
            # easier "did it go up at all".
            if np.isnan(b0) or np.isnan(b1) or b0 == 0:
                continue
            sec_fwd = valr[i + forward] / valr[i] - 1
            ben_fwd = b1 / b0 - 1
            feat.at[idx, "target"] = 1.0 if (sec_fwd - ben_fwd) > margin else 0.0

    return feat


def _build_xgb(scale_pos_weight: float = 1.0):
    import xgboost as xgb

    return xgb.XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
        random_state=42, scale_pos_weight=scale_pos_weight,
    )


def _walk_forward_auc(X: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> float:
    """Mean out-of-fold AUC via expanding-window time-series splits."""
    aucs = []
    for tr, te in TimeSeriesSplit(n_splits=n_splits).split(X):
        ytr, yte = y.iloc[tr], y.iloc[te]
        if ytr.nunique() < 2 or yte.nunique() < 2:
            continue
        spw = (ytr == 0).sum() / max((ytr == 1).sum(), 1)
        m = _build_xgb(spw)
        m.fit(X.iloc[tr], ytr)
        aucs.append(roc_auc_score(yte, m.predict_proba(X.iloc[te])[:, 1]))
    return float(np.mean(aucs)) if aucs else float("nan")


def _backup_existing():
    if os.path.exists(MODEL_PATH):
        day = datetime.now().strftime("%Y%m%d")
        bdir = os.path.join(MODEL_DIR, "backups", day)
        os.makedirs(bdir, exist_ok=True)
        dst = os.path.join(bdir, f"outperformance_{datetime.now():%H%M%S}.pkl")
        shutil.copy2(MODEL_PATH, dst)
        logger.info(f"Backed up existing model → {dst}")


def train(n_splits: int = 5) -> dict:
    """Train, validate, persist, and register the outperformance model."""
    feat = read_sql("SELECT * FROM features")
    if feat.empty:
        raise RuntimeError("No features found — run build_features first.")

    labeled = attach_labels(feat).dropna(subset=["target"]).sort_values("date")
    if labeled.empty:
        raise RuntimeError("No labeled rows (insufficient forward history).")

    X = labeled[FEATURE_COLUMNS]
    y = labeled["target"].astype(int)
    pos_rate = y.mean()
    logger.info(f"Training on {len(labeled)} rows | positive rate {pos_rate:.1%}")

    cv_auc = _walk_forward_auc(X, y, n_splits=n_splits)
    logger.info(f"Walk-forward mean AUC: {cv_auc:.3f}")

    spw = (y == 0).sum() / max((y == 1).sum(), 1)
    model = _build_xgb(spw)
    model.fit(X, y)
    train_acc = accuracy_score(y, model.predict(X))

    os.makedirs(MODEL_DIR, exist_ok=True)
    _backup_existing()
    joblib.dump(
        {"model": model, "features": FEATURE_COLUMNS,
         "metrics": {"cv_auc": cv_auc, "train_acc": train_acc, "pos_rate": float(pos_rate)}},
        MODEL_PATH,
    )
    logger.info(f"Saved model → {MODEL_PATH}")

    execute_sql(
        """INSERT INTO model_registry (model_name, version, auc, accuracy, n_samples, file_path, notes)
           VALUES (:n, :v, :auc, :acc, :ns, :fp, :notes)""",
        {"n": "outperformance", "v": datetime.now().strftime("%Y%m%d_%H%M%S"),
         "auc": cv_auc, "acc": train_acc, "ns": len(labeled), "fp": MODEL_PATH,
         "notes": f"forward={LABEL_FORWARD_DAYS}d margin={LABEL_OUTPERFORM_MARGIN}"},
    )

    # Top feature importances (for logging / sanity).
    imp = sorted(zip(FEATURE_COLUMNS, model.feature_importances_), key=lambda x: -x[1])[:8]
    logger.info("Top features: " + ", ".join(f"{k}={v:.3f}" for k, v in imp))

    return {"cv_auc": cv_auc, "train_acc": train_acc, "n_samples": len(labeled), "pos_rate": float(pos_rate)}
