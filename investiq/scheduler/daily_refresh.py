"""
InvestIQ — daily refresh scheduler.

A background APScheduler job that, after market close, pulls recent data, rebuilds
features, and regenerates recommendations for every risk profile. The investing
cadence is daily, so this replaces the reference project's 30-second scanner.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from utils.logger import get_logger

logger = get_logger("scheduler")


def daily_update():
    """Refresh recent data → rebuild features → regenerate recommendations."""
    try:
        from data.ingest import refresh
        from features.factor_engine import build_features
        from strategy.recommendation_engine import generate

        logger.info("Daily update starting (refresh → features → recommendations) ...")
        refresh(period="1mo")
        build_features(store=True)
        for risk in ("conservative", "balanced", "aggressive"):
            generate(risk_level=risk, store=True)
        logger.info("Daily update complete.")
    except Exception as e:  # noqa: BLE001 - scheduled job must never crash the server
        logger.warning(f"Daily update failed: {e}")


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(daemon=True)
    # 18:30 local — after Indian market close + EOD NAV publication.
    sched.add_job(daily_update, "cron", hour=18, minute=30, id="daily_update", replace_existing=True)
    sched.start()
    logger.info("Scheduler started (daily update at 18:30).")
    return sched
