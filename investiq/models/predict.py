"""
InvestIQ — predictor.

Loads the trained outperformance model and returns P(outperform) for feature rows.
Degrades gracefully (returns a neutral 0.5) when no model has been trained yet.
"""

from __future__ import annotations

import os
from threading import Lock

import joblib
import numpy as np
import pandas as pd

from config.settings import FEATURE_COLUMNS, MODEL_PATH
from utils.logger import get_logger

logger = get_logger("predict")


_CACHE: dict[str, "Predictor"] = {}
_CACHE_LOCK = Lock()


def get_predictor(path: str = MODEL_PATH) -> "Predictor":
    """
    Shared Predictor for a given model path, reloaded only when the file changes.

    The model is ~470KB of pickled XGBoost and every construction deserialized it
    from disk. `/api/health`, `/api/recommendations` and `/api/screener` each built
    a fresh one per request, so a single dashboard page load re-read the model
    several times. Keyed by mtime so a retrain is still picked up without a restart.
    """
    with _CACHE_LOCK:
        cached = _CACHE.get(path)
        stamp = os.path.getmtime(path) if os.path.exists(path) else None
        if cached is not None and cached.loaded_mtime == stamp:
            return cached
        p = Predictor(path)
        _CACHE[path] = p
        return p


class Predictor:
    def __init__(self, path: str = MODEL_PATH):
        self.path = path
        self.model = None
        self.features = FEATURE_COLUMNS
        self.metrics = {}
        self.loaded_mtime = os.path.getmtime(path) if os.path.exists(path) else None
        self.load()

    def load(self) -> bool:
        if not os.path.exists(self.path):
            logger.warning(f"No model at {self.path} — predictions default to 0.5.")
            return False
        bundle = joblib.load(self.path)
        self.model = bundle["model"]
        self.features = bundle.get("features", FEATURE_COLUMNS)
        self.metrics = bundle.get("metrics", {})
        logger.info(f"Loaded outperformance model (cv_auc={self.metrics.get('cv_auc')}).")
        return True

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def predict_proba(self, feat: pd.DataFrame) -> np.ndarray:
        """Return P(outperform) for each row of a feature DataFrame."""
        if feat is None or len(feat) == 0:
            return np.array([])
        if not self.is_loaded:
            return np.full(len(feat), 0.5)
        X = feat.reindex(columns=self.features)
        return self.model.predict_proba(X)[:, 1]
