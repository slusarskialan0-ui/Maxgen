"""Automations router."""
from typing import Optional
from datetime import datetime

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
    a.last_run = datetime.utcnow()
    db.commit()
    return {"ok": True, "runs": a.runs, "automation_id": a.id, "trigger": a.trigger, "action": a.action}


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
