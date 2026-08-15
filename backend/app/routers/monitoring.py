"""System monitoring router."""
import math
import os
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Campaign, ErrorLog, Lead

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

STARTED_AT = time.time()

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


class ErrorLogIn(BaseModel):
    message: str
    source: str = "manual"
    level: str = "error"


def _serialize_error(entry: ErrorLog) -> dict:
    return {
        "id": entry.id,
        "message": entry.message,
        "source": entry.source,
        "level": entry.level,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.get("/health")
def health_details(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.query(Lead.id).limit(1).first()
    except Exception:
        db_ok = False
    memory_mb = 0
    if psutil:
        try:
            memory_mb = round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2)
        except Exception:
            memory_mb = 0
    return {
        "db_ok": db_ok,
        "leads_count": db.query(func.count(Lead.id)).scalar() or 0,
        "campaigns_count": db.query(func.count(Campaign.id)).scalar() or 0,
        "uptime": round(time.time() - STARTED_AT, 1),
        "memory_mb": memory_mb,
    }


@router.get("/errors")
def list_errors(db: Session = Depends(get_db)):
    entries = db.query(ErrorLog).order_by(ErrorLog.created_at.desc()).limit(20).all()
    return [_serialize_error(entry) for entry in entries]


@router.post("/errors", status_code=201)
def create_error(payload: ErrorLogIn, db: Session = Depends(get_db)):
    entry = ErrorLog(message=payload.message, source=payload.source, level=payload.level)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _serialize_error(entry)


@router.get("/stats")
def error_stats(db: Session = Depends(get_db)):
    rows = db.query(ErrorLog.level, func.count(ErrorLog.id)).group_by(ErrorLog.level).all()
    counts = {level: count for level, count in rows}
    return {
        "info": counts.get("info", 0),
        "warning": counts.get("warning", 0),
        "error": counts.get("error", 0),
        "critical": counts.get("critical", 0),
        "total": sum(counts.values()),
    }


@router.post("/restart-sim")
def restart_simulation(db: Session = Depends(get_db)):
    entry = ErrorLog(message="RESTART_REQUESTED", source="monitoring", level="info")
    db.add(entry)
    db.commit()
    return {"ok": True, "message": "Symulacja restartu została zapisana."}


@router.get("/scaling")
def scaling_info(db: Session = Depends(get_db)):
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    max_workers = max(2, min(12, (os.cpu_count() or 2) * 2))
    current_workers = min(max_workers, max(1, math.ceil(total_leads / 50) or 1))
    load_pct = min(100, round((current_workers / max_workers) * 100 + min(35, total_leads / 20), 1))
    return {
        "current_workers": current_workers,
        "max_workers": max_workers,
        "load_pct": load_pct,
    }
