"""Sync router — export/import JSON/CSV, backup, recovery and cleanup."""
import csv
import io
import json
import os
import shutil
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import BackupRecord, EngineEvent, EngineLog, Lead, Offer, Payment

router = APIRouter(prefix="/sync", tags=["sync"])

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "../../../../backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def _lead_dict(l: Lead) -> dict:
    return {
        "id": l.id,
        "project_id": l.project_id,
        "full_name": l.full_name,
        "email": l.email,
        "phone": l.phone,
        "company": l.company,
        "industry": l.industry,
        "voivodeship": l.voivodeship,
        "source": l.source,
        "stage": l.stage,
        "score": l.score,
        "conversion_probability": l.conversion_probability,
        "assigned_to": l.assigned_to,
        "notes": l.notes,
        "tags": l.tags,
        "follow_up_at": l.follow_up_at.isoformat() if l.follow_up_at else None,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }


@router.get("/export/leads/csv")
def export_leads_csv(db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(_lead_dict(leads[0]).keys()) if leads else [
        "id", "project_id", "full_name", "email", "phone", "company", "industry", "voivodeship",
        "source", "stage", "score", "conversion_probability", "assigned_to", "notes", "tags", "follow_up_at", "created_at"
    ])
    writer.writeheader()
    for l in leads:
        writer.writerow(_lead_dict(l))
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"},
    )


@router.get("/export/full/json")
def export_full_snapshot(db: Session = Depends(get_db)):
    data = {
        "leads": [_lead_dict(l) for l in db.query(Lead).order_by(Lead.id).all()],
        "offers": [
            {"id": o.id, "lead_id": o.lead_id, "title": o.title, "amount": o.amount, "status": o.status, "content": o.content}
            for o in db.query(Offer).order_by(Offer.id).all()
        ],
        "payments": [
            {
                "id": p.id,
                "lead_id": p.lead_id,
                "offer_id": p.offer_id,
                "amount": p.amount,
                "status": p.status,
                "method": p.method,
                "confirmation_code": p.confirmation_code,
                "log": p.log,
            }
            for p in db.query(Payment).order_by(Payment.id).all()
        ],
        "events": [
            {"id": e.id, "event_type": e.event_type, "payload_json": e.payload_json, "source": e.source}
            for e in db.query(EngineEvent).order_by(EngineEvent.id).limit(5000).all()
        ],
        "logs": [
            {"id": l.id, "level": l.level, "module": l.module, "message": l.message}
            for l in db.query(EngineLog).order_by(EngineLog.id).limit(5000).all()
        ],
    }
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return StreamingResponse(iter([content]), media_type="application/json", headers={"Content-Disposition": "attachment; filename=offline_snapshot.json"})


@router.post("/import/leads/json")
async def import_leads_json(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        data = json.loads(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Nieprawidłowy plik JSON: {exc}")

    if isinstance(data, dict):
        leads_data = data.get("leads", [])
    else:
        leads_data = data

    added = 0
    skipped = 0
    for item in leads_data:
        email = (item.get("email") or "").strip()
        company = (item.get("company") or "").strip()
        existing = None
        if email:
            existing = db.query(Lead).filter(Lead.email == email).first()
        elif company:
            existing = db.query(Lead).filter(Lead.company == company).first()

        if existing:
            skipped += 1
            continue

        lead = Lead(
            project_id=item.get("project_id", "default"),
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
            assigned_to=item.get("assigned_to", ""),
            score=float(item.get("score", 0) or 0),
            conversion_probability=float(item.get("conversion_probability", 0) or 0),
        )
        db.add(lead)
        added += 1

    db.commit()
    return {"ok": True, "added": added, "skipped": skipped}


@router.post("/backup")
def create_backup(db: Session = Depends(get_db)):
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
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
            snap = {
                "leads": [_lead_dict(l) for l in db.query(Lead).all()],
                "offers": [{"id": o.id, "lead_id": o.lead_id, "amount": o.amount, "status": o.status} for o in db.query(Offer).all()],
                "payments": [{"id": p.id, "lead_id": p.lead_id, "amount": p.amount, "status": p.status} for p in db.query(Payment).all()],
            }
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(snap, f, ensure_ascii=False)
            size = os.path.getsize(dest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    rec = BackupRecord(filename=filename, size_bytes=size, status="ok")
    db.add(rec)
    db.commit()
    return {"ok": True, "filename": filename, "size_bytes": size}


@router.get("/backups")
def list_backups(db: Session = Depends(get_db)):
    records = db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).limit(50).all()
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
        raise HTTPException(status_code=422, detail="Najnowsza kopia to JSON. Użyj /sync/import/leads/json.")
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail=f"Plik kopii nie istnieje: {record.filename}")

    live_db = None
    for candidate in ["polska_leads.db", os.path.join(os.path.dirname(__file__), "../../../../backend/polska_leads.db")]:
        if os.path.exists(candidate):
            live_db = candidate
            break

    if live_db is None:
        raise HTTPException(status_code=500, detail="Nie można zlokalizować aktywnej bazy danych")

    safety_ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
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


@router.post("/auto-clean")
def auto_clean(days: int = 30, db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=max(1, min(days, 365)))
    removed_logs = db.query(EngineLog).filter(EngineLog.created_at < cutoff).delete(synchronize_session=False)
    removed_events = db.query(EngineEvent).filter(EngineEvent.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "removed": int(removed_logs or 0) + int(removed_events or 0), "cutoff": cutoff.isoformat()}
