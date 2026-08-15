from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import B2BLead
from app.pipeline.pipeline import run_b2b_pipeline

router = APIRouter(prefix="/b2b", tags=["b2b"])


@router.post("/scan")
def scan_b2b(db: Session = Depends(get_db)):
    return run_b2b_pipeline(db)


@router.get("/leads")
def list_b2b_leads(
    min_score: int = Query(default=0, ge=0, le=100),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(B2BLead)
        .filter(B2BLead.lead_score >= min_score)
        .order_by(B2BLead.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "source_name": r.source_name,
            "external_id": r.external_id,
            "title": r.title,
            "budget_pln": r.budget_pln,
            "vat_required": r.vat_required,
            "description": r.description,
            "contact_phone": r.contact_phone,
            "contact_email": r.contact_email,
            "location": r.location,
            "work_mode": r.work_mode,
            "direct_link": r.direct_link,
            "lead_score": r.lead_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
