"""
InvestIQ — entry point.

Modes:
  mock       Generate a synthetic universe; --load writes it to the investiq DB.
  ingest     Pull real MF/equity data into the DB.            (later PR)
  train      Train the outperformance model.                  (later PR)
  backtest   Backtest the strategy vs benchmark.              (later PR)
  recommend  Compute today's BUY/HOLD/SELL recommendations.   (later PR)
  serve      Run the Flask API.                               (later PR)

Usage:
  python investiq/main.py mock
  python investiq/main.py mock --load
"""

import argparse
import os
import sys

# Make the module importable no matter the current working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import get_logger

logger = get_logger("main")


def run_mock(load: bool = False, years: float = 4.0):
    from data.mock_data import generate_all_mock_data, load_mock_data_to_db

    logger.info("=" * 60)
    logger.info("MODE: MOCK — generating synthetic investing universe")
    logger.info("=" * 60)

    data = generate_all_mock_data(years=years)
    secs = data["securities"]
    logger.info(
        f"Securities: {len(secs)} "
        f"({(secs['sec_type'] == 'MF').sum()} MF, "
        f"{(secs['sec_type'] == 'EQUITY').sum()} equity, "
        f"{(secs['sec_type'] == 'INDEX').sum()} index)"
    )
    logger.info(f"NAV rows:   {len(data['nav_history'])}")
    logger.info(f"Price rows: {len(data['price_history'])}")
    logger.info(f"Fundamentals rows: {len(data['fundamentals'])}")
    if len(data["price_history"]):
        ph = data["price_history"]
        logger.info(f"Date range: {ph['date'].min()} → {ph['date'].max()}")

    if load:
        logger.info("Loading mock data into the investiq DB ...")
        counts = load_mock_data_to_db()
        logger.info(f"Rows written (new): {counts}")

    logger.info("Mock dataset ready.")


def run_ingest(sample: bool = False, period: str = "5y"):
    from data.ingest import run_ingest as _ingest

    logger.info("=" * 60)
    logger.info(f"MODE: INGEST — real data ({'sample' if sample else 'full universe'})")
    logger.info("=" * 60)
    _ingest(sample=sample, period=period)


def run_train():
    from features.factor_engine import build_features
    from models.train_model import train

    logger.info("=" * 60)
    logger.info("MODE: TRAIN — outperformance model")
    logger.info("=" * 60)
    logger.info("Rebuilding features ...")
    build_features(store=True)
    metrics = train()
    logger.info(f"Training metrics: {metrics}")


def run_recommend(risk: str = "balanced"):
    from features.factor_engine import build_features
    from strategy.recommendation_engine import generate

    logger.info("=" * 60)
    logger.info(f"MODE: RECOMMEND — {risk} profile")
    logger.info("=" * 60)
    build_features(store=True)
    scored = generate(risk_level=risk, store=True)
    if scored.empty:
        return
    buys = scored[scored["action"] == "BUY"].head(10)
    logger.info(f"Top BUYs ({len(scored[scored['action'] == 'BUY'])} total):")
    for _, r in buys.iterrows():
        logger.info(f"  BUY  {r['symbol']:<14} {str(r['name'])[:32]:<32} score={r['final_score']:.2f}  ({r['rationale']})")


def run_backtest(risk: str = "balanced"):
    import json

    from backtest.backtest_engine import run_backtest as _bt

    logger.info("=" * 60)
    logger.info(f"MODE: BACKTEST — {risk} profile (monthly factor-rank vs Nifty)")
    logger.info("=" * 60)
    res = _bt(risk_level=risk)
    logger.info(f"Metrics: {res['metrics']}")

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_results")
    os.makedirs(out_dir, exist_ok=True)
    eq = res["equity_curve"]
    payload = {
        "risk": risk,
        "metrics": res["metrics"],
        "equity_curve": [
            {"date": str(r["date"]), "strategy": round(float(r["strategy"]), 4),
             "benchmark": round(float(r["benchmark"]), 4)}
            for _, r in eq.iterrows()
        ],
    }
    with open(os.path.join(out_dir, f"{risk}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info(f"Saved backtest_results/{risk}.json")


def run_serve(port: int = 5055):
    from backend.app import app
    from scheduler.daily_refresh import start_scheduler

    logger.info("=" * 60)
    logger.info(f"MODE: SERVE — Flask API on http://localhost:{port}")
    logger.info("=" * 60)
    start_scheduler()
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


def _not_yet(mode: str):
    logger.warning(f"Mode '{mode}' is not implemented yet (added in a later PR).")
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser(description="InvestIQ entry point")
    parser.add_argument(
        "mode",
        choices=["mock", "ingest", "train", "backtest", "recommend", "serve"],
    )
    parser.add_argument("--load", action="store_true", help="mock: write to the investiq DB")
    parser.add_argument("--years", type=float, default=4.0, help="mock: years of history")
    parser.add_argument("--sample", action="store_true", help="ingest: small subset for a quick test")
    parser.add_argument("--period", default="5y", help="ingest: yfinance history period (e.g. 5y, 1mo)")
    parser.add_argument("--risk", default="balanced",
                        choices=["conservative", "balanced", "aggressive"], help="recommend: risk profile")
    parser.add_argument("--port", type=int, default=5055, help="serve: API port")
    args = parser.parse_args()

    if args.mode == "mock":
        run_mock(load=args.load, years=args.years)
    elif args.mode == "ingest":
        run_ingest(sample=args.sample, period=args.period)
    elif args.mode == "train":
        run_train()
    elif args.mode == "recommend":
        run_recommend(risk=args.risk)
    elif args.mode == "backtest":
        run_backtest(risk=args.risk)
    elif args.mode == "serve":
        run_serve(port=args.port)
    else:
        _not_yet(args.mode)


if __name__ == "__main__":
    main()
