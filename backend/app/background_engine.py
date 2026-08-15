from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.data.geography import VOIVODESHIPS
from app.models.models import Lead, VoivodeshipStatus
from app.routers.auto_ops import (
    BACKUP_DIR,
    _export_payload,
    LeadGenerationPayload,
    bootstrap,
    generate_campaigns,
    generate_leads,
    run_sales_automation,
    simulate_payments,
)
from config import (
    AUTO_BACKUP_EVERY_CYCLES,
    AUTO_BACKUP_KEEP_LATEST,
    AUTO_BACKGROUND_ENABLED,
    AUTO_BACKGROUND_INTERVAL_SECONDS,
    AUTO_BACKGROUND_LEADS_LIMIT,
    AUTO_SELF_HEAL_STALLED_PIPELINE,
)
from database import SessionLocal

logger = logging.getLogger(__name__)

_state = {
    "enabled": AUTO_BACKGROUND_ENABLED,
    "running": False,
    "cycle": 0,
    "last_started_at": None,
    "last_finished_at": None,
    "last_success_at": None,
    "last_error": None,
    "last_voivodeship": None,
    "last_backup_file": None,
    "last_backup_at": None,
    "last_maintenance_error": None,
    "interval_seconds": AUTO_BACKGROUND_INTERVAL_SECONDS,
    "leads_limit": AUTO_BACKGROUND_LEADS_LIMIT,
    "backup_every_cycles": AUTO_BACKUP_EVERY_CYCLES,
    "backup_keep_latest": AUTO_BACKUP_KEEP_LATEST,
}
_bg_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None
_voivodeship_index = 0
_state_lock = Lock()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_background_engine_status() -> dict:
    with _state_lock:
        snapshot = {**_state}
    return {**snapshot, "task_alive": bool(_bg_task and not _bg_task.done())}


def _pick_voivodeship() -> str:
    global _voivodeship_index
    with _state_lock:
        voivodeship = VOIVODESHIPS[_voivodeship_index % len(VOIVODESHIPS)]
        _voivodeship_index += 1
    return voivodeship


def _run_cycle_once() -> None:
    db = SessionLocal()
    try:
        bootstrap(db)
        voivodeship = _pick_voivodeship()
        payload = LeadGenerationPayload(
            voivodeship=voivodeship,
            industries=[],
            limit=AUTO_BACKGROUND_LEADS_LIMIT,
        )
        generate_leads(payload, db)
        run_sales_automation(db)
        generate_campaigns(db)
        simulate_payments(db)
        with _state_lock:
            _state["last_voivodeship"] = voivodeship
    finally:
        db.close()


def _write_backup_snapshot(db) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    payload = _export_payload(db)
    filename = BACKUP_DIR / f"backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    filename.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return filename.name


def _cleanup_backups(keep_latest: int) -> int:
    keep_latest = max(1, keep_latest)
    backups: list[Path] = sorted(BACKUP_DIR.glob("backup-*.json"))
    removable = backups[:-keep_latest] if len(backups) > keep_latest else []
    for item in removable:
        item.unlink(missing_ok=True)
    return len(removable)


def _heal_stalled_pipeline(db) -> int:
    if not AUTO_SELF_HEAL_STALLED_PIPELINE:
        return 0
    rows = (
        db.query(VoivodeshipStatus)
        .filter(VoivodeshipStatus.status.in_(["w_trakcie", "in_progress"]))
        .all()
    )
    for row in rows:
        row.status = "nie_rozpoczete"
    if rows:
        db.commit()
    return len(rows)


def _normalize_pending_leads(db) -> int:
    stale = (
        db.query(Lead)
        .filter(Lead.stage == "nowy", Lead.follow_up_at.is_(None))
        .limit(1000)
        .all()
    )
    now = datetime.now(timezone.utc)
    for lead in stale:
        lead.follow_up_at = now
    if stale:
        db.commit()
    return len(stale)


def _run_maintenance_cycle(cycle_number: int) -> None:
    if cycle_number % AUTO_BACKUP_EVERY_CYCLES != 0:
        return
    db = SessionLocal()
    try:
        backup_name = _write_backup_snapshot(db)
        removed = _cleanup_backups(AUTO_BACKUP_KEEP_LATEST)
        healed = _heal_stalled_pipeline(db)
        normalized = _normalize_pending_leads(db)
        with _state_lock:
            _state["last_backup_file"] = backup_name
            _state["last_backup_at"] = _ts()
            _state["last_maintenance_error"] = None
        logger.info(
            "Maintenance done: backup=%s removed=%s healed=%s normalized=%s",
            backup_name,
            removed,
            healed,
            normalized,
        )
    except Exception as exc:
        with _state_lock:
            _state["last_maintenance_error"] = str(exc)
        logger.exception("Maintenance cycle failed: %s", exc)
    finally:
        db.close()


async def _background_loop() -> None:
    if _stop_event is None:
        raise RuntimeError("Background engine stop event not initialized")
    while not _stop_event.is_set():
        with _state_lock:
            _state["running"] = True
            _state["last_started_at"] = _ts()
        try:
            await asyncio.to_thread(_run_cycle_once)
            with _state_lock:
                _state["cycle"] += 1
                _state["last_error"] = None
                _state["last_success_at"] = _ts()
                cycle_number = _state["cycle"]
            await asyncio.to_thread(_run_maintenance_cycle, cycle_number)
        except Exception as exc:
            with _state_lock:
                _state["last_error"] = str(exc)
            logger.exception("Background engine cycle failed: %s", exc)
        finally:
            with _state_lock:
                _state["last_finished_at"] = _ts()

        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=AUTO_BACKGROUND_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue

    with _state_lock:
        _state["running"] = False


async def start_background_engine() -> None:
    global _bg_task, _stop_event
    if not AUTO_BACKGROUND_ENABLED:
        with _state_lock:
            _state["enabled"] = False
            _state["running"] = False
        return
    if _bg_task and not _bg_task.done():
        return
    _stop_event = asyncio.Event()
    _bg_task = asyncio.create_task(_background_loop())


async def stop_background_engine() -> None:
    global _bg_task
    if _stop_event:
        _stop_event.set()
    if _bg_task:
        await asyncio.gather(_bg_task, return_exceptions=True)
    _bg_task = None
    with _state_lock:
        _state["running"] = False
