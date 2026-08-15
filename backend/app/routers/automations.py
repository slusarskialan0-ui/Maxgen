"""Automations router."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Automation

router = APIRouter(prefix="/automations", tags=["automations"])


class AutomationIn(BaseModel):
    name: str
    trigger: str = "new_lead"
    action: str = "assign"
    condition_json: str = "{}"
    enabled: bool = True


class AutomationUpdate(BaseModel):
    name: Optional[str] = None
    trigger: Optional[str] = None
    action: Optional[str] = None
    condition_json: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("")
def list_automations(db: Session = Depends(get_db)):
    return [_ser(a) for a in db.query(Automation).order_by(Automation.id).all()]


@router.post("", status_code=201)
def create_automation(payload: AutomationIn, db: Session = Depends(get_db)):
    a = Automation(**payload.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return _ser(a)


@router.patch("/{automation_id}")
def update_automation(automation_id: int, payload: AutomationUpdate, db: Session = Depends(get_db)):
    a = db.query(Automation).filter(Automation.id == automation_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Automatyzacja nie znaleziona")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return _ser(a)


@router.delete("/{automation_id}", status_code=204)
def delete_automation(automation_id: int, db: Session = Depends(get_db)):
    a = db.query(Automation).filter(Automation.id == automation_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Automatyzacja nie znaleziona")
    db.delete(a)
    db.commit()


@router.post("/{automation_id}/run")
def run_automation_now(automation_id: int, db: Session = Depends(get_db)):
    a = db.query(Automation).filter(Automation.id == automation_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Automatyzacja nie znaleziona")
    a.runs += 1
    a.last_run = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "runs": a.runs}


@router.post("/run-due-follow-ups")
def run_due_follow_ups(db: Session = Depends(get_db)):
    """Process all leads with overdue follow-ups: re-score and reschedule."""
    from app.models.models import Lead
    now = datetime.now(timezone.utc)
    due_leads = (
        db.query(Lead)
        .filter(Lead.follow_up_at <= now, Lead.stage.not_in(["wygrany", "przegrany"]))
        .all()
    )
    processed = 0
    for lead in due_leads:
        lead.follow_up_at = now + timedelta(days=1)
        lead.score = _rescore_lead(lead)
        processed += 1
    db.commit()
    return {"ok": True, "processed": processed}


@router.post("/batch-score")
def batch_score_leads(db: Session = Depends(get_db)):
    """Re-run scoring for all open leads and update conversion probabilities."""
    from app.models.models import Lead
    stage_weights = {"nowy": 0.05, "kontakt": 0.20, "negocjacje": 0.50}
    leads = db.query(Lead).filter(Lead.stage.not_in(["wygrany", "przegrany"])).all()
    updated = 0
    for lead in leads:
        lead.score = _rescore_lead(lead)
        base = stage_weights.get(lead.stage, 0.10)
        lead.conversion_probability = round(min(max(base * 0.6 + (lead.score / 100.0) * 0.4, 0), 1), 3)
        updated += 1
    db.commit()
    return {"ok": True, "updated": updated}


def _rescore_lead(lead) -> float:
    score = 20.0
    if lead.email:
        score += 20
    if lead.phone:
        score += 15
    if lead.company or lead.company_name:
        score += 10
    if lead.industry:
        score += 10
    if lead.voivodeship:
        score += 5
    if lead.notes and len(lead.notes) > 20:
        score += 10
    if lead.campaign_id:
        score += 10
    return round(min(max(score, 0), 100), 1)


def _ser(a: Automation) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "trigger": a.trigger,
        "action": a.action,
        "condition_json": a.condition_json,
        "enabled": a.enabled,
        "runs": a.runs,
        "last_run": a.last_run.isoformat() if a.last_run else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
