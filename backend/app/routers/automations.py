"""Automations router."""
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Automation, Lead

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
    return {"ok": True, "runs": a.runs}


@router.post("/generate-offer/{lead_id}")
def generate_offer(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    offer_text = (
        f"Oferta dla {lead.full_name or lead.company or f'Leada #{lead.id}'}\n\n"
        f"Dziękujemy za zainteresowanie usługami dla branży {lead.industry or 'motoryzacyjnej'} w województwie "
        f"{lead.voivodeship or 'mazowieckim'}.\n"
        f"Proponujemy wdrożenie pakietu pozyskiwania leadów, obsługi kampanii i automatyzacji kontaktu.\n"
        f"Rekomendowany priorytet: score AI {lead.score}/100, szansa konwersji {round((lead.conversion_probability or 0) * 100)}%.\n"
        "Zakres: konfiguracja kampanii, obsługa follow-up, raportowanie i wsparcie sprzedaży.\n"
        "Prosimy o kontakt zwrotny w celu doprecyzowania budżetu i harmonogramu."
    )
    note = f"\n[OFERTA {datetime.utcnow().isoformat()}]\n{offer_text}"
    lead.notes = f"{lead.notes or ''}{note}".strip()
    db.commit()
    return {"ok": True, "lead_id": lead.id, "offer": offer_text}


@router.post("/close-stale")
def close_stale_leads(db: Session = Depends(get_db)):
    threshold = datetime.utcnow() - timedelta(days=30)
    leads = (
        db.query(Lead)
        .filter(Lead.stage == "nowy", Lead.created_at <= threshold)
        .all()
    )
    for lead in leads:
        lead.stage = "przegrany"
        lead.closed_at = datetime.utcnow()
        lead.conversion_probability = 0.0
    db.commit()
    return {"ok": True, "closed": len(leads)}


@router.get("/predictions")
def predictions(db: Session = Depends(get_db)):
    leads = (
        db.query(Lead)
        .filter(Lead.stage.not_in(["wygrany", "przegrany"]))
        .order_by(Lead.conversion_probability.desc(), Lead.score.desc())
        .all()
    )
    return [
        {
            "id": lead.id,
            "full_name": lead.full_name,
            "company": lead.company,
            "industry": lead.industry,
            "stage": lead.stage,
            "score": lead.score,
            "conversion_probability": lead.conversion_probability,
            "assigned_to": lead.assigned_to,
        }
        for lead in leads
    ]


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
