"""
InvestIQ — Flask API (port 5055).

Serves recommendations, the paper portfolio, security details, screener, backtest,
and market overview to the Next.js dashboard. Investing cadence is daily, so there
is no SSE/30s scanner — a background APScheduler job refreshes data once a day.

Run: python main.py serve   (or python backend/app.py)
"""

import json
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

from config.risk_profiles import RiskLevel, list_profiles
from config.settings import BENCHMARK_SYMBOL, FEATURE_COLUMNS
from database.db import read_sql
from models.predict import get_predictor
from portfolio.paper_portfolio import PaperPortfolio
from strategy.recommendation_engine import generate
from utils.logger import get_logger

logger = get_logger("api")

app = Flask(__name__)
CORS(app)  # allow the Next.js dev server


def records(df: pd.DataFrame) -> list:
    """DataFrame → JSON-native list of dicts (handles numpy types + dates)."""
    if df is None or df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _security_names() -> dict:
    s = read_sql("SELECT symbol, name FROM securities")
    return dict(zip(s["symbol"], s["name"]))


class BadRequest(Exception):
    """A client supplied an invalid parameter."""


@app.errorhandler(BadRequest)
def _bad_request(e):
    return jsonify({"error": str(e)}), 400


_VALID_RISK = {lvl.value for lvl in RiskLevel}


def _risk_arg(default: str = "balanced") -> str:
    """
    Read and validate the `risk` query parameter against the RiskLevel enum.

    Every caller previously passed this string through unchecked, which was wrong in
    three different ways:
      - `generate()` feeds it to RiskLevel(...), so a bad value raised ValueError and
        surfaced as an opaque 500 instead of a 400;
      - /api/market/overview interpolated it into a SQL filter, so a bad value quietly
        returned empty breadth — a wrong answer rather than an error;
      - /api/backtest joined it into a FILE PATH, so `?risk=../../<path>` escaped the
        results directory and read arbitrary .json files off disk.
    Whitelisting against the enum closes all three.
    """
    risk = request.args.get("risk", default)
    if risk not in _VALID_RISK:
        raise BadRequest(
            f"invalid risk '{risk}' — expected one of {sorted(_VALID_RISK)}"
        )
    return risk


# ── System ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    counts = read_sql(
        """SELECT
             (SELECT count(*) FROM securities) AS securities,
             (SELECT count(*) FROM price_history) AS price_rows,
             (SELECT count(*) FROM nav_history)  AS nav_rows,
             (SELECT count(*) FROM features)     AS feature_rows"""
    ).iloc[0].to_dict()
    return jsonify({
        "status": "ok",
        "model_loaded": get_predictor().is_loaded,
        "counts": {k: int(v) for k, v in counts.items()},
    })


@app.get("/api/risk/profiles")
def risk_profiles():
    return jsonify(list_profiles())


@app.get("/api/refresh/status")
def refresh_status():
    from scheduler.daily_refresh import last_run

    row = read_sql(
        """SELECT (SELECT max(date) FROM price_history) AS last_price_date,
                  (SELECT max(date) FROM nav_history)  AS last_nav_date,
                  (SELECT max(date) FROM features)     AS last_feature_date"""
    )
    out = records(row)[0] if not row.empty else {}
    out["last_run"] = last_run()  # so a silently failing nightly job is visible
    return jsonify(out)


# ── Universe / recommendations / screener ───────────────────────────────────────
@app.get("/api/securities")
def securities():
    df = read_sql(
        "SELECT symbol, name, sec_type, category, fund_house, benchmark "
        "FROM securities WHERE active=true ORDER BY sec_type, name"
    )
    return jsonify(records(df))


def _held_symbols() -> set:
    h = PaperPortfolio().holdings()
    return set(h["symbol"]) if not h.empty else set()


@app.get("/api/recommendations")
def recommendations():
    risk = _risk_arg()
    scored = generate(risk_level=risk, held=_held_symbols(), store=False)
    if scored.empty:
        return jsonify([])
    cols = ["symbol", "name", "category", "sec_type", "action", "final_score",
            "ml_prob", "factor_score", "risk_score", "momentum_score", "rationale"]
    return jsonify(records(scored[cols]))


@app.get("/api/screener")
def screener():
    """Full scored universe with optional filters (sec_type, action, min_score)."""
    risk = _risk_arg()
    scored = generate(risk_level=risk, held=_held_symbols(), store=False)
    if scored.empty:
        return jsonify([])
    if (st := request.args.get("sec_type")):
        scored = scored[scored["sec_type"] == st]
    if (act := request.args.get("action")):
        scored = scored[scored["action"] == act]
    if (ms := request.args.get("min_score")):
        scored = scored[scored["final_score"] >= float(ms)]
    cols = ["symbol", "name", "category", "sec_type", "action", "final_score",
            "ml_prob", "factor_score", "risk_score", "momentum_score",
            "volatility", "sharpe", "ret_1y", "rationale"]
    return jsonify(records(scored[cols]))


@app.get("/api/security/<path:symbol>")
def security_detail(symbol):
    risk = _risk_arg()
    sec = read_sql("SELECT * FROM securities WHERE symbol=:s", {"s": symbol})
    if sec.empty:
        return jsonify({"error": "not found"}), 404
    s = sec.iloc[0]
    if s["sec_type"] == "MF":
        hist = read_sql(
            "SELECT date, nav AS value FROM nav_history WHERE scheme_code=:c ORDER BY date",
            {"c": s["scheme_code"]},
        )
    else:
        hist = read_sql(
            "SELECT date, close AS value FROM price_history WHERE symbol=:s ORDER BY date",
            {"s": symbol},
        )
    hist = hist.tail(750)  # ~3y for charting
    feat = read_sql(
        "SELECT * FROM features WHERE symbol=:s ORDER BY date DESC LIMIT 1", {"s": symbol}
    )
    rec = read_sql(
        "SELECT * FROM recommendations WHERE symbol=:s AND risk_level=:r "
        "ORDER BY date DESC LIMIT 1",
        {"s": symbol, "r": risk},
    )
    fund = read_sql(
        "SELECT * FROM fundamentals WHERE symbol=:s ORDER BY date DESC LIMIT 1", {"s": symbol}
    )
    return jsonify({
        "security": records(sec)[0],
        "history": records(hist),
        "features": records(feat)[0] if not feat.empty else {},
        "recommendation": records(rec)[0] if not rec.empty else {},
        "fundamentals": records(fund)[0] if not fund.empty else {},
    })


# ── Portfolio ───────────────────────────────────────────────────────────────────
@app.get("/api/portfolio")
def portfolio():
    pf = PaperPortfolio()
    h = pf.holdings()
    names = _security_names()
    if not h.empty:
        h = h.copy()
        h["name"] = h["symbol"].map(names).fillna(h["symbol"])
    summary = {k: (float(v) if isinstance(v, float) else v) for k, v in pf.summary().items()}
    return jsonify({"summary": summary, "holdings": records(h)})


@app.post("/api/portfolio/buy")
def portfolio_buy():
    body = request.get_json(force=True) or {}
    res = PaperPortfolio().buy(body["symbol"], float(body.get("amount", 0)))
    return jsonify({"ok": res is not None, "order": res})


@app.post("/api/portfolio/sell")
def portfolio_sell():
    body = request.get_json(force=True) or {}
    res = PaperPortfolio().sell(body["symbol"], float(body.get("fraction", 1.0)))
    return jsonify({"ok": res is not None, "order": res})


@app.post("/api/portfolio/rebalance")
def portfolio_rebalance():
    from portfolio.rebalancer import rebalance

    risk = (request.get_json(silent=True) or {}).get("risk") or request.args.get("risk", "balanced")
    if risk not in _VALID_RISK:
        raise BadRequest(f"invalid risk '{risk}' — expected one of {sorted(_VALID_RISK)}")
    summary = {k: (float(v) if isinstance(v, float) else v) for k, v in rebalance(risk).items()}
    return jsonify({"ok": True, "summary": summary})


@app.get("/api/portfolio/history")
def portfolio_history():
    df = read_sql(
        "SELECT date, total_value, invested, cash, pnl FROM portfolio_snapshots "
        "WHERE mode='paper' ORDER BY date"
    )
    return jsonify(records(df))


def _cache_is_stale(path: str) -> bool:
    """
    True when the cached backtest predates the newest feature row.

    A backtest is a pure function of the `features` table plus price history, so the
    max feature date is the right invalidation signal: any refresh that adds data
    makes an earlier run obsolete. Fails closed (treats the cache as stale) if the
    check itself errors, so a DB hiccup yields a fresh compute rather than stale data.
    """
    try:
        newest = read_sql("SELECT max(date) AS d FROM features")["d"].iloc[0]
        if newest is None:
            return False
        cached_at = datetime.fromtimestamp(os.path.getmtime(path)).date()
        return cached_at <= pd.Timestamp(newest).date()
    except Exception as e:  # noqa: BLE001 - never let cache checking break the route
        logger.warning(f"Backtest cache staleness check failed ({e}) — recomputing.")
        return True


# ── Market / backtest ────────────────────────────────────────────────────────────
@app.get("/api/market/overview")
def market_overview():
    risk = _risk_arg()
    bench = read_sql(
        "SELECT date, close FROM price_history WHERE symbol=:s ORDER BY date DESC LIMIT 22",
        {"s": BENCHMARK_SYMBOL},
    )
    last = chg_1d = chg_1m = None
    if not bench.empty:
        last = float(bench["close"].iloc[0])
        if len(bench) > 1:
            chg_1d = last / float(bench["close"].iloc[1]) - 1
        chg_1m = last / float(bench["close"].iloc[-1]) - 1
    # Scope BOTH the filter and the max(date) subquery to the profile — profiles can
    # be generated on different dates, and an unscoped max(date) would then return
    # no rows for the lagging one.
    breadth = read_sql(
        "SELECT action, count(*) n FROM recommendations WHERE risk_level=:r "
        "AND date=(SELECT max(date) FROM recommendations WHERE risk_level=:r) "
        "GROUP BY action",
        {"r": risk},
    )
    return jsonify({
        "benchmark": BENCHMARK_SYMBOL, "last": last,
        "change_1d": chg_1d, "change_1m": chg_1m,
        "risk": risk,
        "breadth": {r["action"]: int(r["n"]) for _, r in breadth.iterrows()},
    })


@app.get("/api/backtest")
def backtest():
    risk = _risk_arg()
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "backtest_results", f"{risk}.json")

    # Serve the cached run only while it is newer than the newest feature row it was
    # computed from. The previous `if os.path.exists(path)` had no invalidation at
    # all: once main.py wrote balanced.json it was served verbatim forever, while
    # profiles with no cache file recomputed fresh on every call — so the same
    # endpoint was simultaneously permanently stale for one profile and live for the
    # others, with no way to tell which you were looking at.
    if os.path.exists(path) and not _cache_is_stale(path):
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        payload["cached"] = True
        return jsonify(payload)

    from backtest.backtest_engine import run_backtest

    res = run_backtest(risk_level=risk)
    payload = {"risk": risk, "metrics": res["metrics"],
               "equity_curve": records(res["equity_curve"]), "cached": False}
    try:  # refresh the cache so the next request is cheap
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except OSError as e:  # a read-only deploy must still serve the response
        logger.warning(f"Could not write backtest cache {path}: {e}")
    return jsonify(payload)


if __name__ == "__main__":
    from scheduler.daily_refresh import start_scheduler

    start_scheduler()
    app.run(host="0.0.0.0", port=int(os.getenv("INVESTIQ_PORT", "5055")), debug=False, threaded=True)
