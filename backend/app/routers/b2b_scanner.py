"""B2B Scanner API — trigger scraping runs, list leads, toggle scanner."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/b2b", tags=["b2b"])

_scanner_running = False
_scheduler_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    sources: Optional[list[str]] = None  # ["olx", "useme", "oferteo"] or None = all


# ---------------------------------------------------------------------------
# Background scan job
# ---------------------------------------------------------------------------

async def _scan_and_store() -> int:
    """Run the full B2B scrape → score → dedup → store pipeline."""
    global _scanner_running
    _scanner_running = True
    stored = 0
    try:
        from app.sources.b2b_scraper import scrape_b2b_orders
        from app.pipeline.b2b_scorer import compute_lead_score, deduplicate_orders
        from database import SessionLocal
        from app.models.models import B2BLead, SystemConfig

        orders = scrape_b2b_orders()
        if not orders:
            logger.info("B2B scan: no orders fetched")
            return 0

        db = SessionLocal()
        try:
            # Load existing hashes + titles for dedup
            existing = db.query(B2BLead.content_hash, B2BLead.title).all()
            existing_hashes = {row.content_hash for row in existing}
            existing_titles = [row.title for row in existing]

            unique_orders = deduplicate_orders(orders, existing_hashes, existing_titles)

            threshold_row = db.query(SystemConfig).filter_by(key="B2B_LEAD_SCORE_THRESHOLD").first()
            threshold = int(threshold_row.value) if threshold_row else int(os.getenv("B2B_LEAD_SCORE_THRESHOLD", "65"))

            for order in unique_orders:
                score = compute_lead_score(
                    title=order.title,
                    description=order.description,
                    budget=order.budget,
                    fvat_required=order.fvat_required,
                    source=order.source,
                    contact_info=order.contact_info,
                )
                lead = B2BLead(
                    external_id=order.external_id,
                    title=order.title,
                    budget=order.budget,
                    fvat_required=order.fvat_required,
                    description=order.description,
                    contact_info=json.dumps(order.contact_info, ensure_ascii=False),
                    score=score,
                    url=order.url,
                    source=order.source,
                    content_hash=order.content_hash,
                    sent_to_telegram=False,
                )
                db.add(lead)
                db.flush()
                stored += 1

            db.commit()

            # PUSH alerts for high-score leads (after commit so rows are visible)
            for lead in db.query(B2BLead).filter(
                B2BLead.score >= threshold, B2BLead.sent_to_telegram == False
            ).order_by(B2BLead.created_at.desc()).limit(stored).all():
                asyncio.create_task(_push_telegram(lead))
            logger.info("B2B scan: stored %d new leads (out of %d fetched)", stored, len(orders))
        finally:
            db.close()
    except Exception as exc:
        logger.error("B2B scan job error: %s", exc)
    finally:
        _scanner_running = False
    return stored


def enqueue_scan() -> str:
    """Start scan in background if scanner is idle."""
    global _scanner_running
    if _scanner_running:
        return "already_running"
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return "no_event_loop"
    _scanner_running = True
    loop.create_task(_scan_and_store())
    return "started"


async def _push_telegram(lead) -> None:
    try:
        from app.routers.telegram_bot import push_lead_alert
        sent = await push_lead_alert(lead)
        if sent:
            from database import SessionLocal
            from app.models.models import B2BLead
            db = SessionLocal()
            try:
                row = db.query(B2BLead).filter_by(id=lead.id).first()
                if row:
                    row.sent_to_telegram = True
                    db.commit()
            finally:
                db.close()
    except Exception as exc:
        logger.warning("Telegram push failed: %s", exc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/scan")
async def trigger_scan():
    """Trigger a one-off B2B scraping run in the background."""
    return {"status": enqueue_scan()}


@router.get("/leads")
def list_leads(
    min_score: int = Query(0, ge=0, le=100),
    fvat_only: bool = False,
    min_budget: Optional[float] = None,
    source: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = 0,
):
    """List scraped B2B leads with filters."""
    from database import SessionLocal
    from app.models.models import B2BLead

    db = SessionLocal()
    try:
        q = db.query(B2BLead)
        if min_score:
            q = q.filter(B2BLead.score >= min_score)
        if fvat_only:
            q = q.filter(B2BLead.fvat_required == True)
        if min_budget is not None:
            q = q.filter(B2BLead.budget >= min_budget)
        if source:
            q = q.filter(B2BLead.source == source)
        total = q.count()
        items = q.order_by(B2BLead.score.desc(), B2BLead.created_at.desc()).offset(offset).limit(limit).all()
        return {
            "total": total,
            "items": [
                {
                    "id": l.id,
                    "title": l.title,
                    "score": l.score,
                    "budget": l.budget,
                    "fvat_required": l.fvat_required,
                    "source": l.source,
                    "url": l.url,
                    "contact_info": _safe_json(l.contact_info),
                    "description": l.description[:300] if l.description else "",
                    "sent_to_telegram": l.sent_to_telegram,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in items
            ],
        }
    finally:
        db.close()


def _safe_json(val):
    if not val:
        return {}
    if isinstance(val, dict):
        return val
    try:
        return json.loads(val)
    except Exception:
        return {}


@router.get("/scanner/status")
def scanner_status():
    """Return whether the auto-scanner is running."""
    from database import SessionLocal
    from app.models.models import SystemConfig
    db = SessionLocal()
    try:
        row = db.query(SystemConfig).filter_by(key="b2b_scanner_enabled").first()
        enabled = row.value == "true" if row else False
    finally:
        db.close()
    return {"running": _scanner_running, "enabled": enabled}


@router.post("/scanner/toggle")
def toggle_scanner():
    """Enable or disable the auto-scanner."""
    from database import SessionLocal
    from app.models.models import SystemConfig
    db = SessionLocal()
    try:
        row = db.query(SystemConfig).filter_by(key="b2b_scanner_enabled").first()
        current = row.value == "true" if row else False
        new_val = "false" if current else "true"
        if row:
            row.value = new_val
        else:
            db.add(SystemConfig(key="b2b_scanner_enabled", value=new_val))
        db.commit()
        return {"enabled": new_val == "true"}
    finally:
        db.close()


async def _scheduler_loop():
    interval = int(os.getenv("B2B_SCAN_INTERVAL_SECONDS", "900"))
    logger.info("B2B scheduler started (interval=%ss)", interval)
    while True:
        await asyncio.sleep(interval)
        try:
            from database import SessionLocal
            from app.models.models import SystemConfig
            db = SessionLocal()
            try:
                row = db.query(SystemConfig).filter_by(key="b2b_scanner_enabled").first()
                enabled = row.value == "true" if row else False
            finally:
                db.close()

            if enabled:
                status = enqueue_scan()
                logger.info("B2B scheduler tick: %s", status)
        except Exception as exc:
            logger.error("B2B scheduler error: %s", exc)


def start_b2b_scheduler():
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    _scheduler_task = asyncio.create_task(_scheduler_loop())
