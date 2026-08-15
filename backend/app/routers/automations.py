"""Automations router."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Automation, Lead, Offer, UserProfile

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


@router.post("/run-full-cycle")
def run_full_cycle(db: Session = Depends(get_db)):
    """Lead → assign → offer → follow-up → close (for high confidence leads)."""
    now = datetime.now(timezone.utc)
    open_leads = db.query(Lead).filter(Lead.stage.not_in(["wygrany", "przegrany"])).all()
    if not open_leads:
        return {"ok": True, "processed": 0, "assigned": 0, "offers_created": 0, "followups_scheduled": 0, "closed": 0}

    active_agents = (
        db.query(UserProfile.username, func.count(Lead.id).label("lead_count"))
        .outerjoin(
            Lead,
            (Lead.assigned_to == UserProfile.username) & Lead.stage.not_in(["wygrany", "przegrany"]),
        )
        .filter(UserProfile.active.is_(True), UserProfile.role.in_(["agent", "manager"]))
        .group_by(UserProfile.username)
        .order_by(func.count(Lead.id).asc(), UserProfile.username.asc())
        .all()
    )
    agent_usernames = [u for u, _ in active_agents]

    assigned = 0
    offers_created = 0
    followups_scheduled = 0
    closed = 0
    scored = 0

    for idx, lead in enumerate(open_leads):
        lead.score = _rescore_lead(lead)
        scored += 1
        base = {"nowy": 0.05, "kontakt": 0.20, "negocjacje": 0.50}.get(lead.stage, 0.10)
        lead.conversion_probability = round(min(max(base * 0.6 + (lead.score / 100.0) * 0.4, 0), 1), 3)

        if agent_usernames and not (lead.assigned_to or "").strip():
            lead.assigned_to = agent_usernames[idx % len(agent_usernames)]
            assigned += 1

        if lead.score >= 60:
            has_offer = db.query(Offer.id).filter(Offer.lead_id == lead.id).first()
            if not has_offer:
                amount = float(max(499.0, round((lead.score * 37.5), 2)))
                offer = Offer(
                    lead_id=lead.id,
                    title=f"Auto-oferta dla {lead.company or lead.full_name or 'Leada'}",
                    description="Oferta wygenerowana automatycznie przez silnik sprzedaży.",
                    amount=amount,
                    status="sent",
                    sent_at=now,
                )
                db.add(offer)
                offers_created += 1

        follow_up_at = lead.follow_up_at
        if follow_up_at and follow_up_at.tzinfo is None:
            follow_up_at = follow_up_at.replace(tzinfo=timezone.utc)
        if follow_up_at is None or follow_up_at <= now:
            lead.follow_up_at = now + timedelta(hours=24)
            followups_scheduled += 1

        if lead.score >= 90 or lead.conversion_probability >= 0.92:
            lead.stage = "wygrany"
            lead.closed_at = now
            lead.conversion_probability = 1.0
            closed += 1
        elif lead.stage == "nowy" and lead.score >= 45:
            lead.stage = "kontakt"
        elif lead.stage == "kontakt" and lead.score >= 70:
            lead.stage = "negocjacje"

    db.commit()
    return {
        "ok": True,
        "processed": len(open_leads),
        "scored": scored,
        "assigned": assigned,
        "offers_created": offers_created,
        "followups_scheduled": followups_scheduled,
        "closed": closed,
    }


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
