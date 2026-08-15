"""Health check endpoint + Cron-Sweeper background job.

Cron-Sweeper runs weekly and removes B2BLeads older than 30 days,
preventing the free DB plan from filling up.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

_START_TIME = time.time()
_sweeper_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/health")
def health():
    """Keep-alive endpoint — returns 200 OK with DB ping and uptime."""
    uptime_seconds = int(time.time() - _START_TIME)
    db_status = "ok"
    b2b_leads_count = 0
    try:
        from database import SessionLocal
        from app.models.models import B2BLead
        db = SessionLocal()
        try:
            b2b_leads_count = db.query(B2BLead).count()
        finally:
            db.close()
    except Exception as exc:
        logger.error("Health DB check error: %s", exc)
        db_status = "error"

    return {
        "status": "ok",
        "uptime_seconds": uptime_seconds,
        "database": db_status,
        "b2b_leads_total": b2b_leads_count,
        "ts": int(time.time()),
    }


# ---------------------------------------------------------------------------
# Cron Sweeper
# ---------------------------------------------------------------------------

async def _run_cron_sweeper() -> None:
    """Weekly job: delete B2BLeads older than 30 days."""
    interval = 7 * 24 * 3600  # one week
    while True:
        await asyncio.sleep(interval)
        try:
            from database import SessionLocal
            from app.models.models import B2BLead
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            db = SessionLocal()
            try:
                deleted = (
                    db.query(B2BLead)
                    .filter(B2BLead.created_at < cutoff)
                    .delete(synchronize_session=False)
                )
                db.commit()
                logger.info("Cron-Sweeper: deleted %d old B2B leads", deleted)
            finally:
                db.close()
        except Exception as exc:
            logger.error("Cron-Sweeper error: %s", exc)


def start_cron_sweeper() -> None:
    """Schedule the sweeper task (call once during app startup)."""
    global _sweeper_task
    loop = asyncio.get_running_loop()
    _sweeper_task = loop.create_task(_run_cron_sweeper())
    logger.info("Cron-Sweeper scheduled (interval=7d, retention=30d)")
