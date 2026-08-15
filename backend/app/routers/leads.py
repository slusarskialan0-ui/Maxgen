"""Leads router — CRUD, webhooks, AI scoring, follow-up automation."""
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Lead, Campaign, Automation, UserProfile

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadIn(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""
    industry: str = ""
    voivodeship: str = ""
    source: str = "manual"
    campaign_id: Optional[int] = None
    assigned_to: str = ""
    stage: str = "nowy"
    notes: str = ""
    tags: str = ""
    project_id: str = "default"


class LeadUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    voivodeship: Optional[str] = None
    stage: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    follow_up_at: Optional[datetime] = None


class WebhookPayload(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""
    industry: str = ""
    voivodeship: str = ""
    source: str = "webhook"
    campaign_id: Optional[int] = None
    project_id: str = "default"
    extra: dict = {}


def _compute_score(lead: Lead) -> float:
    """Simple heuristic scoring: 0-100."""
    score = 20.0
    if lead.email:
        score += 20
    if lead.phone:
        score += 15
    if lead.company:
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


def _compute_conversion(score: float, stage: str) -> float:
    """Predict conversion probability 0-1."""
    stage_weights = {
        "nowy": 0.05,
        "kontakt": 0.20,
        "negocjacje": 0.50,
        "wygrany": 1.0,
        "przegrany": 0.0,
    }
    base = stage_weights.get(stage, 0.10)
    score_factor = score / 100.0
    prob = base * 0.6 + score_factor * 0.4
    return round(min(max(prob, 0), 1), 3)


def _auto_assign(db: Session) -> str:
    """Round-robin assignment to active users."""
    users = db.query(UserProfile).filter(UserProfile.active == True, UserProfile.role.in_(["agent", "manager"])).all()
    if not users:
        return ""
    counts = {}
    for u in users:
        counts[u.username] = db.query(Lead).filter(Lead.assigned_to == u.username, Lead.stage.not_in(["wygrany", "przegrany"])).count()
    return min(counts, key=counts.get)


def _run_automations(lead_id: int):
    from database import SessionLocal

    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return
        automations = db.query(Automation).filter(Automation.enabled == True).all()
        for auto in automations:
            triggered = False
            if auto.trigger == "new_lead":
                triggered = True
            elif auto.trigger == "score_above":
                try:
                    cond = json.loads(auto.condition_json)
                    triggered = lead.score >= float(cond.get("threshold", 70))
                except Exception:
                    pass
            if triggered:
                if auto.action == "assign" and not lead.assigned_to:
                    lead.assigned_to = _auto_assign(db)
                elif auto.action == "follow_up" and not lead.follow_up_at:
                    lead.follow_up_at = datetime.utcnow() + timedelta(days=1)
                auto.runs += 1
                auto.last_run = datetime.utcnow()
        lead.score = _compute_score(lead)
        lead.conversion_probability = _compute_conversion(lead.score, lead.stage)
        db.commit()
    finally:
        db.close()


@router.get("")
def list_leads(
    stage: Optional[str] = None,
    source: Optional[str] = None,
    assigned_to: Optional[str] = None,
    campaign_id: Optional[int] = None,
    voivodeship: Optional[str] = None,
    industry: Optional[str] = None,
    min_score: Optional[float] = None,
    project_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(Lead)
    if stage:
        q = q.filter(Lead.stage == stage)
    if source:
        q = q.filter(Lead.source == source)
    if assigned_to:
        q = q.filter(Lead.assigned_to == assigned_to)
    if campaign_id:
        q = q.filter(Lead.campaign_id == campaign_id)
    if voivodeship:
        q = q.filter(Lead.voivodeship == voivodeship)
    if industry:
        q = q.filter(Lead.industry == industry)
    if min_score is not None:
        q = q.filter(Lead.score >= min_score)
    if project_id:
        q = q.filter(Lead.project_id == project_id)
    total = q.count()
    items = q.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_serialize(l) for l in items]}


@router.post("", status_code=201)
def create_lead(payload: LeadIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    lead = Lead(**payload.model_dump())
    if not lead.assigned_to:
        lead.assigned_to = _auto_assign(db)
    lead.score = _compute_score(lead)
    lead.conversion_probability = _compute_conversion(lead.score, lead.stage)
    if not lead.follow_up_at:
        lead.follow_up_at = datetime.utcnow() + timedelta(days=1)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    background_tasks.add_task(_run_automations, lead.id)
    if lead.campaign_id:
        c = db.query(Campaign).filter(Campaign.id == lead.campaign_id).first()
        if c:
            c.current_leads = (c.current_leads or 0) + 1
            db.commit()
    return _serialize(lead)


@router.get("/funnel")
def funnel_stats(db: Session = Depends(get_db)):
    stages = ["nowy", "kontakt", "negocjacje", "wygrany", "przegrany"]
    rows = db.query(Lead.stage, func.count(Lead.id)).group_by(Lead.stage).all()
    counts = {r[0]: r[1] for r in rows}
    total = sum(counts.values()) or 1
    return {
        "stages": [
            {"stage": s, "count": counts.get(s, 0), "pct": round(counts.get(s, 0) / total * 100, 1)}
            for s in stages
        ],
        "total": total,
    }


@router.get("/due-follow-ups")
def due_follow_ups(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    leads = (
        db.query(Lead)
        .filter(Lead.follow_up_at <= now, Lead.stage.not_in(["wygrany", "przegrany"]))
        .order_by(Lead.follow_up_at)
        .limit(50)
        .all()
    )
    return [_serialize(l) for l in leads]


@router.get("/ai-prediction")
def ai_prediction(db: Session = Depends(get_db)):
    """Returns conversion predictions and top leads to focus on."""
    leads = db.query(Lead).filter(Lead.stage.not_in(["wygrany", "przegrany"])).all()
    top = sorted(leads, key=lambda l: l.conversion_probability, reverse=True)[:10]
    avg_score = round(sum(l.score for l in leads) / len(leads), 1) if leads else 0
    avg_prob = round(sum(l.conversion_probability for l in leads) / len(leads) * 100, 1) if leads else 0
    return {
        "avg_score": avg_score,
        "avg_conversion_pct": avg_prob,
        "top_leads": [_serialize(l) for l in top],
        "total_open": len(leads),
    }


@router.get("/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    l = db.query(Lead).filter(Lead.id == lead_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    return _serialize(l)


@router.patch("/{lead_id}")
def update_lead(lead_id: int, payload: LeadUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    l = db.query(Lead).filter(Lead.id == lead_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(l, k, v)
    if payload.stage == "wygrany":
        l.closed_at = datetime.utcnow()
        l.conversion_probability = 1.0
    elif payload.stage == "przegrany":
        l.closed_at = datetime.utcnow()
        l.conversion_probability = 0.0
    l.score = _compute_score(l)
    if payload.stage and payload.stage not in ["wygrany", "przegrany"]:
        l.conversion_probability = _compute_conversion(l.score, l.stage)
    l.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(l)
    background_tasks.add_task(_run_automations, l.id)
    return _serialize(l)


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    l = db.query(Lead).filter(Lead.id == lead_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    db.delete(l)
    db.commit()


@router.post("/webhook")
def webhook_lead(payload: WebhookPayload, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Public webhook endpoint — accepts leads from external sources."""
    lead = Lead(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        industry=payload.industry,
        voivodeship=payload.voivodeship,
        source=payload.source,
        campaign_id=payload.campaign_id,
        project_id=payload.project_id,
        stage="nowy",
    )
    lead.assigned_to = _auto_assign(db)
    lead.score = _compute_score(lead)
    lead.conversion_probability = _compute_conversion(lead.score, lead.stage)
    lead.follow_up_at = datetime.utcnow() + timedelta(days=1)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    background_tasks.add_task(_run_automations, lead.id)
    return {"ok": True, "lead_id": lead.id, "score": lead.score}


def _serialize(l: Lead) -> dict:
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
        "campaign_id": l.campaign_id,
        "assigned_to": l.assigned_to,
        "stage": l.stage,
        "score": l.score,
        "conversion_probability": l.conversion_probability,
        "notes": l.notes,
        "tags": l.tags,
        "follow_up_at": l.follow_up_at.isoformat() if l.follow_up_at else None,
        "closed_at": l.closed_at.isoformat() if l.closed_at else None,
        "created_at": l.created_at.isoformat() if l.created_at else None,
        "updated_at": l.updated_at.isoformat() if l.updated_at else None,
    }
