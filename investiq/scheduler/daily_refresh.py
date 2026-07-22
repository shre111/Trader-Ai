"""
InvestIQ — daily refresh scheduler.

A background APScheduler job that, after market close, pulls recent data, rebuilds
features, and regenerates recommendations for every risk profile. The investing
cadence is daily, so this replaces the reference project's 30-second scanner.
"""

from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from utils.logger import get_logger

logger = get_logger("scheduler")


_LAST_RUN: dict = {"started_at": None, "finished_at": None, "status": "never_run", "error": None}


def last_run() -> dict:
    """Outcome of the most recent daily update (surfaced via /api/refresh/status)."""
    return dict(_LAST_RUN)


def daily_update():
    """Refresh recent data → rebuild features → regenerate recommendations."""
    from data.ingest import refresh
    from features.factor_engine import build_features
    from portfolio.paper_portfolio import PaperPortfolio
    from strategy.recommendation_engine import generate

    _LAST_RUN.update(started_at=datetime.now().isoformat(), finished_at=None,
                     status="running", error=None)
    logger.info("Daily update starting (refresh → features → recommendations) ...")
    try:
        refresh(period="1mo")
        build_features(store=True)
        # Pass current holdings, exactly as the API does. `generate()` uses `held` to
        # keep an owned name at HOLD rather than re-issuing BUY; omitting it here meant
        # the STORED recommendations were computed as if the portfolio were empty, so
        # they disagreed with the live /api/recommendations response for every holding.
        held = PaperPortfolio().holdings()
        held_syms = set(held["symbol"]) if not held.empty else set()
        for risk in ("conservative", "balanced", "aggressive"):
            generate(risk_level=risk, held=held_syms, store=True)
    except Exception as e:  # noqa: BLE001 - a scheduled job must not kill the server
        # Still swallowed (APScheduler would otherwise drop the job), but recorded at
        # ERROR with a traceback and exposed via last_run(). Previously this was a bare
        # warning with no stack and no state, so a nightly job could fail every night
        # and the dashboard would keep serving silently stale data with no signal.
        _LAST_RUN.update(finished_at=datetime.now().isoformat(), status="failed", error=str(e))
        logger.error(f"Daily update FAILED: {e}", exc_info=True)
        return
    _LAST_RUN.update(finished_at=datetime.now().isoformat(), status="ok", error=None)
    logger.info("Daily update complete.")


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(daemon=True)
    # 18:30 local — after Indian market close + EOD NAV publication.
    sched.add_job(daily_update, "cron", hour=18, minute=30, id="daily_update", replace_existing=True)
    sched.start()
    logger.info("Scheduler started (daily update at 18:30).")
    return sched
