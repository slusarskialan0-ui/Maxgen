"""Sync router — export/import CSV/JSON, backup, recovery."""
import csv
import io
import json
import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db, SessionLocal, engine
from app.models.models import Lead, BackupRecord

router = APIRouter(prefix="/sync", tags=["sync"])

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "../../../../backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


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
