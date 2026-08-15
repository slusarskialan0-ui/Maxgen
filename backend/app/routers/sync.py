"""Sync router — export/import CSV/JSON, backup, recovery."""
import csv
import io
import json
import os
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db, SessionLocal, engine
from app.models.models import Lead, BackupRecord, IntegrationJob
from app.background_engine import get_background_engine_status

router = APIRouter(prefix="/sync", tags=["sync"])

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "../../../../backups")
os.makedirs(BACKUP_DIR, exist_ok=True)
CONNECTOR_NAMES = {"local_csv", "local_json", "webhook"}


@router.get("/export/leads/csv")
def export_leads_csv(db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "full_name", "email", "phone", "company", "industry", "voivodeship",
        "source", "stage", "score", "conversion_probability", "assigned_to",
        "notes", "tags", "follow_up_at", "created_at"
    ])
    writer.writeheader()
    for l in leads:
        writer.writerow({
            "id": l.id, "full_name": l.full_name, "email": l.email,
            "phone": l.phone, "company": l.company, "industry": l.industry,
            "voivodeship": l.voivodeship, "source": l.source, "stage": l.stage,
            "score": l.score, "conversion_probability": l.conversion_probability,
            "assigned_to": l.assigned_to, "notes": l.notes, "tags": l.tags,
            "follow_up_at": l.follow_up_at.isoformat() if l.follow_up_at else "",
            "created_at": l.created_at.isoformat() if l.created_at else "",
        })
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"},
    )


@router.get("/export/leads/json")
def export_leads_json(db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    data = [
        {
            "id": l.id, "full_name": l.full_name, "email": l.email,
            "phone": l.phone, "company": l.company, "industry": l.industry,
            "voivodeship": l.voivodeship, "source": l.source, "stage": l.stage,
            "score": l.score, "conversion_probability": l.conversion_probability,
            "assigned_to": l.assigned_to, "notes": l.notes, "tags": l.tags,
            "follow_up_at": l.follow_up_at.isoformat() if l.follow_up_at else None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in leads
    ]
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=leads_export.json"},
    )


@router.post("/import/leads/json")
async def import_leads_json(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        data = json.loads(content)
    except Exception:
        raise HTTPException(status_code=400, detail="Nieprawidłowy plik JSON")
    added = 0
    for item in data:
        email = item.get("email", "").strip()
        company = item.get("company", "").strip()
        # Dedup: skip if a lead with the same email already exists (email is the primary unique key)
        if email:
            existing = db.query(Lead).filter(Lead.email == email).first()
        elif company:
            existing = db.query(Lead).filter(Lead.company == company).first()
        else:
            existing = None
        if not existing:
            l = Lead(
                full_name=item.get("full_name", ""),
                email=item.get("email", ""),
                phone=item.get("phone", ""),
                company=item.get("company", ""),
                industry=item.get("industry", ""),
                voivodeship=item.get("voivodeship", ""),
                source=item.get("source", "import"),
                stage=item.get("stage", "nowy"),
                notes=item.get("notes", ""),
                tags=item.get("tags", ""),
            )
            db.add(l)
            added += 1
    db.commit()
    return {"ok": True, "added": added, "skipped": len(data) - added}


@router.post("/backup")
def create_backup(db: Session = Depends(get_db)):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    db_path = os.path.join(os.path.dirname(__file__), "../../../../backend/polska_leads.db")
    if not os.path.exists(db_path):
        db_path = "polska_leads.db"
    filename = f"backup_{ts}.db"
    dest = os.path.join(BACKUP_DIR, filename)
    size = 0
    try:
        if os.path.exists(db_path):
            shutil.copy2(db_path, dest)
            size = os.path.getsize(dest)
        else:
            filename = f"backup_{ts}.json"
            dest = os.path.join(BACKUP_DIR, filename)
            leads = db.query(Lead).all()
            snap = [{"id": l.id, "email": l.email, "company": l.company, "stage": l.stage} for l in leads]
            with open(dest, "w") as f:
                json.dump(snap, f)
            size = os.path.getsize(dest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    rec = BackupRecord(filename=filename, size_bytes=size, status="ok")
    db.add(rec)
    db.commit()
    return {"ok": True, "filename": filename, "size_bytes": size}


@router.post("/auto-backup")
def auto_backup(db: Session = Depends(get_db)):
    return create_backup(db)


@router.get("/backups")
def list_backups(db: Session = Depends(get_db)):
    records = db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).limit(20).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "size_bytes": r.size_bytes,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.post("/recovery")
def trigger_recovery(db: Session = Depends(get_db)):
    record = db.query(BackupRecord).filter(BackupRecord.status == "ok").order_by(BackupRecord.created_at.desc()).first()
    if not record:
        raise HTTPException(status_code=404, detail="Brak kopii zapasowej")

    backup_path = os.path.join(BACKUP_DIR, record.filename)
    if not backup_path.endswith(".db"):
        raise HTTPException(
            status_code=422,
            detail=f"Najnowsza kopia ({record.filename}) jest w formacie JSON — odtwarzanie pliku .db jest niedostępne. Użyj /sync/import/leads/json.",
        )
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail=f"Plik kopii nie istnieje: {record.filename}")

    # Locate the live DB file
    live_db = None
    for candidate in [
        "polska_leads.db",
        os.path.join(os.path.dirname(__file__), "../../../../backend/polska_leads.db"),
    ]:
        if os.path.exists(candidate):
            live_db = candidate
            break

    if live_db is None:
        raise HTTPException(
            status_code=500,
            detail="Nie można zlokalizować aktywnej bazy danych — odtwarzanie niemożliwe.",
        )

    # Create a safety snapshot before overwriting
    safety_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safety_path = os.path.join(BACKUP_DIR, f"pre_recovery_{safety_ts}.db")
    try:
        shutil.copy2(live_db, safety_path)
        shutil.copy2(backup_path, live_db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Odtwarzanie nie powiodło się: {exc}")

    return {
        "ok": True,
        "recovered_from": record.filename,
        "safety_snapshot": os.path.basename(safety_path),
        "message": "Baza danych odtworzona. Uruchom ponownie serwer, aby zastosować zmiany.",
    }


@router.post("/auto-recovery")
def auto_recovery(db: Session = Depends(get_db)):
    return trigger_recovery(db)


@router.post("/auto-clean")
def auto_clean(keep_latest: int = 10, db: Session = Depends(get_db)):
    removed_backups, removed_files = _clean_old_backups(db, keep_latest)
    updated_leads = _normalize_pending_leads(db)
    return {
        "ok": True,
        "removed_backups": removed_backups,
        "removed_files": removed_files,
        "updated_leads": updated_leads,
    }


def _clean_old_backups(db: Session, keep_latest: int) -> tuple[int, int]:
    keep_latest = max(0, keep_latest)
    records = db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).all()
    to_delete = records[keep_latest:]
    removed_files = 0
    for rec in to_delete:
        path = os.path.join(BACKUP_DIR, rec.filename)
        if os.path.exists(path):
            os.remove(path)
            removed_files += 1
        db.delete(rec)
    db.commit()
    return len(to_delete), removed_files


def _normalize_pending_leads(db: Session) -> int:
    old_pending = (
        db.query(Lead)
        .filter(Lead.stage == "nowy", Lead.follow_up_at.is_(None))
        .limit(1000)
        .all()
    )
    for lead in old_pending:
        lead.follow_up_at = datetime.now(timezone.utc)
    db.commit()
    return len(old_pending)


@router.get("/auto-status")
def auto_status(db: Session = Depends(get_db)):
    latest = db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).first()
    engine_status = get_background_engine_status()
    pending_jobs = (
        db.query(IntegrationJob)
        .filter(IntegrationJob.status.in_(["pending", "failed", "processing"]))
        .count()
    )
    dead_jobs = db.query(IntegrationJob).filter(IntegrationJob.status == "dead_letter").count()
    return {
        "auto_backup": "enabled",
        "auto_recovery": "enabled",
        "auto_clean": "enabled",
        "background_engine": engine_status,
        "latest_backup": latest.filename if latest else None,
        "latest_backup_at": latest.created_at.isoformat() if latest and latest.created_at else None,
        "integration_queue": {
            "pending_or_retrying": pending_jobs,
            "dead_letter": dead_jobs,
        },
    }


@router.get("/connectors")
def list_connectors(db: Session = Depends(get_db)):
    rows = (
        db.query(IntegrationJob.connector, IntegrationJob.status, func.count(IntegrationJob.id))
        .group_by(IntegrationJob.connector, IntegrationJob.status)
        .all()
    )
    summary = {
        name: {"pending": 0, "processing": 0, "failed": 0, "done": 0, "dead_letter": 0}
        for name in sorted(CONNECTOR_NAMES)
    }
    for connector, status, count in rows:
        if connector in summary and status in summary[connector]:
            summary[connector][status] = int(count or 0)
    return {"connectors": summary}


@router.post("/connectors/{connector}/enqueue")
def enqueue_connector_job(connector: str, payload: Optional[dict] = Body(default=None), db: Session = Depends(get_db)):
    if connector not in CONNECTOR_NAMES:
        raise HTTPException(status_code=404, detail=f"Nieznany konektor: {connector}")
    job = IntegrationJob(
        connector=connector,
        direction="sync",
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
        status="pending",
        max_attempts=3,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"ok": True, "job_id": job.id, "connector": connector, "status": job.status}


@router.get("/connectors/jobs")
def list_connector_jobs(limit: int = 50, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    jobs = db.query(IntegrationJob).order_by(IntegrationJob.created_at.desc()).limit(limit).all()
    return [
        {
            "id": j.id,
            "connector": j.connector,
            "direction": j.direction,
            "status": j.status,
            "attempts": j.attempts,
            "max_attempts": j.max_attempts,
            "next_retry_at": j.next_retry_at.isoformat() if j.next_retry_at else None,
            "last_error": j.last_error,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "updated_at": j.updated_at.isoformat() if j.updated_at else None,
        }
        for j in jobs
    ]


@router.post("/connectors/run-pending")
def run_pending_connector_jobs(limit: int = 20, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    limit = max(1, min(limit, 200))
    pending = (
        db.query(IntegrationJob)
        .filter(
            IntegrationJob.status.in_(["pending", "failed"]),
            (IntegrationJob.next_retry_at.is_(None)) | (IntegrationJob.next_retry_at <= now),
        )
        .order_by(IntegrationJob.created_at.asc())
        .limit(limit)
        .all()
    )
    processed = 0
    done = 0
    failed = 0
    dead_letter = 0
    for job in pending:
        processed += 1
        _run_job(job, db, now)
        if job.status == "done":
            done += 1
        elif job.status == "dead_letter":
            dead_letter += 1
        elif job.status == "failed":
            failed += 1
    db.commit()
    return {
        "ok": True,
        "processed": processed,
        "done": done,
        "failed": failed,
        "dead_letter": dead_letter,
    }


def _run_job(job: IntegrationJob, db: Session, now: datetime) -> None:
    job.status = "processing"
    job.attempts = int(job.attempts or 0) + 1
    try:
        payload = json.loads(job.payload_json or "{}")
        result = _execute_connector(job.connector, payload, db)
        job.status = "done"
        job.result_json = json.dumps(result, ensure_ascii=False)
        job.next_retry_at = None
        job.last_error = ""
    except Exception as exc:
        job.last_error = str(exc)
        if job.attempts >= max(1, int(job.max_attempts or 3)):
            job.status = "dead_letter"
            job.next_retry_at = None
        else:
            backoff_minutes = min(60, job.attempts * 2)
            job.status = "failed"
            job.next_retry_at = now.replace(microsecond=0) + timedelta(minutes=backoff_minutes)


def _execute_connector(connector: str, payload: dict, db: Session) -> dict:
    if connector == "local_csv":
        export_leads_csv(db)
        return {"message": "CSV export generated", "type": "local_csv"}
    if connector == "local_json":
        export_leads_json(db)
        return {"message": "JSON export generated", "type": "local_json"}
    if connector == "webhook":
        url = str(payload.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("Webhook connector wymaga poprawnego URL")
        body = json.dumps(
            payload.get("data") or {"event": "sync.ping", "ts": datetime.now(timezone.utc).isoformat()},
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                status = int(getattr(response, "status", 200))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Webhook call failed: {exc}")
        if status >= 400:
            raise RuntimeError(f"Webhook returned status {status}")
        return {"message": "Webhook delivered", "status_code": status}
    raise ValueError(f"Unsupported connector: {connector}")
