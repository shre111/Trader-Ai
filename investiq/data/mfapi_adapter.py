"""
InvestIQ — api.mfapi.in adapter (free mutual fund NAV data).

Resolves fund name substrings to scheme codes (preferring Direct-Growth plans) and
fetches full daily NAV history + scheme metadata. No credentials required.
"""

from __future__ import annotations

import pandas as pd
import requests

from utils.logger import get_logger

logger = get_logger("mfapi")

BASE = "https://api.mfapi.in/mf"
_session = requests.Session()
_session.headers.update({"User-Agent": "InvestIQ/0.1"})
_all_schemes: list | None = None


def get_all_schemes() -> list:
    """Return (and cache) the full list of schemes: [{schemeCode, schemeName}, ...]."""
    global _all_schemes
    if _all_schemes is None:
        r = _session.get(BASE, timeout=30)
        r.raise_for_status()
        _all_schemes = r.json()
        logger.info(f"Loaded {len(_all_schemes)} schemes from mfapi.")
    return _all_schemes


def resolve_scheme(name_substring: str, prefer=("direct", "growth")) -> dict | None:
    """
    Find the best scheme matching `name_substring`. Among matches, prefer plans
    whose name contains all `prefer` keywords (e.g. Direct + Growth), then the
    shortest name (usually the plain plan). Returns {schemeCode, schemeName} or None.
    """
    q = name_substring.lower()
    matches = [s for s in get_all_schemes() if q in s["schemeName"].lower()]
    if not matches:
        return None

    def rank(s):
        n = s["schemeName"].lower()
        pref_hits = sum(k in n for k in prefer)
        idcw_penalty = 1 if ("idcw" in n or "dividend" in n) else 0
        return (-pref_hits, idcw_penalty, len(n))

    matches.sort(key=rank)
    return matches[0]


def fetch_nav_history(scheme_code: str) -> tuple[pd.DataFrame, dict]:
    """Return (DataFrame[date, nav] ascending, metadata dict) for a scheme code."""
    r = _session.get(f"{BASE}/{scheme_code}", timeout=30)
    r.raise_for_status()
    payload = r.json()
    meta = payload.get("meta", {}) or {}
    rows = payload.get("data", []) or []
    df = pd.DataFrame(rows)
    if df.empty:
        return df, meta
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y").dt.date
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["nav"]).sort_values("date").reset_index(drop=True)
    return df[["date", "nav"]], meta
