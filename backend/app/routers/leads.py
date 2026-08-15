"""Leads router — CRUD, webhooks, AI scoring, follow-up automation."""
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Lead, Campaign, Automation, UserProfile, Offer

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


class OfflineLeadGeneratorIn(BaseModel):
    traffic: int = 100
    campaign_name: str = "Kampania offline"
    source_mix: dict = Field(default_factory=lambda: {
        "ads_offline": 0.35,
        "social_offline": 0.25,
        "marketplace_offline": 0.20,
        "forms_offline": 0.20,
    })
    industry: str = "motoryzacja"
    voivodeship: str = "mazowieckie"
    project_id: str = "default"


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
        automations = (
            db.query(Automation)
            .filter(
                Automation.enabled == True,
                or_(Automation.automation_type.is_(None), Automation.automation_type == ""),
            )
            .all()
        )
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
                    lead.follow_up_at = datetime.now(timezone.utc) + timedelta(days=1)
                elif auto.action == "close" and lead.stage not in ["wygrany", "przegrany"]:
                    lead.stage = "wygrany"
                    lead.closed_at = datetime.now(timezone.utc)
                    lead.conversion_probability = 1.0
                elif auto.action == "offer":
                    existing_offer = (
                        db.query(Offer)
                        .filter(Offer.lead_id == lead.id, Offer.status.in_(["draft", "sent", "accepted"]))
                        .first()
                    )
                    if not existing_offer:
                        db.add(
                            Offer(
                                project_id=lead.project_id,
                                lead_id=lead.id,
                                title=f"Oferta dla {lead.company or lead.full_name or f'Leada #{lead.id}'}",
                                description="Automatycznie wygenerowana oferta sprzedażowa.",
                                amount=round(1000 + (lead.score * 120), 2),
                                currency="PLN",
                                status="sent",
                                sent_at=datetime.now(timezone.utc),
                            )
                        )
                elif auto.action == "predict":
                    lead.conversion_probability = _compute_conversion(lead.score, lead.stage)
                auto.runs += 1
                auto.last_run = datetime.now(timezone.utc)
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
        lead.follow_up_at = datetime.now(timezone.utc) + timedelta(days=1)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    background_tasks.add_task(_run_automations, lead.id)
    # lead count for campaign is computed dynamically via _bulk_lead_counts; no increment needed
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
    now = datetime.now(timezone.utc)
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
        l.closed_at = datetime.now(timezone.utc)
        l.conversion_probability = 1.0
    elif payload.stage == "przegrany":
        l.closed_at = datetime.now(timezone.utc)
        l.conversion_probability = 0.0
    l.score = _compute_score(l)
    if payload.stage and payload.stage not in ["wygrany", "przegrany"]:
        l.conversion_probability = _compute_conversion(l.score, l.stage)
    l.updated_at = datetime.now(timezone.utc)
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
    lead.follow_up_at = datetime.now(timezone.utc) + timedelta(days=1)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    background_tasks.add_task(_run_automations, lead.id)
    return {"ok": True, "lead_id": lead.id, "score": lead.score}


@router.post("/generate-offline")
def generate_offline_leads(payload: OfflineLeadGeneratorIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Offline lead generator: traffic -> campaign -> leads + scoring + customer behavior."""
    campaign = db.query(Campaign).filter(Campaign.name == payload.campaign_name, Campaign.project_id == payload.project_id).first()
    if not campaign:
        campaign = Campaign(
            project_id=payload.project_id,
            name=payload.campaign_name,
            source="offline_mix",
            target_leads=max(10, int(payload.traffic * 0.35)),
            status="aktywna",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

    source_weights = payload.source_mix or {}
    sources = list(source_weights.keys()) or ["ads_offline", "social_offline", "marketplace_offline", "forms_offline"]
    weights = [max(0, float(source_weights.get(s, 0))) for s in sources]
    if not any(weights):
        weights = [1 for _ in sources]

    generated = []
    lead_target = max(1, int(payload.traffic * random.uniform(0.15, 0.42)))
    for i in range(lead_target):
        source = random.choices(sources, weights=weights, k=1)[0]
        behavior = random.choice(["aktywny", "porownuje_oferty", "gotowy_do_zakupu", "wymaga_followup"])
        stage = random.choices(["nowy", "kontakt", "negocjacje"], weights=[0.5, 0.35, 0.15], k=1)[0]
        lead = Lead(
            project_id=payload.project_id,
            full_name=f"Lead Offline {campaign.id}-{i+1}",
            email=f"offline_{campaign.id}_{i+1}@lead.local",
            phone=f"+48{random.randint(500000000, 899999999)}",
            company=f"Firma Offline {i+1}",
            industry=payload.industry,
            voivodeship=payload.voivodeship,
            source=source,
            campaign_id=campaign.id,
            assigned_to=_auto_assign(db),
            stage=stage,
            notes=f"behavior={behavior}; traffic={payload.traffic}",
            tags=f"offline,{behavior}",
        )
        lead.score = _compute_score(lead) + random.uniform(0, 15)
        lead.score = round(min(100, lead.score), 1)
        lead.conversion_probability = _compute_conversion(lead.score, lead.stage)
        if behavior in ["aktywny", "wymaga_followup"] and not lead.follow_up_at:
            lead.follow_up_at = datetime.now(timezone.utc) + timedelta(hours=random.randint(12, 48))
        db.add(lead)
        db.flush()
        generated.append(lead.id)

    db.commit()
    for lead_id in generated:
        background_tasks.add_task(_run_automations, lead_id)
    return {
        "ok": True,
        "campaign_id": campaign.id,
        "traffic": payload.traffic,
        "generated_leads": len(generated),
        "lead_ids": generated,
    }


def _serialize(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "project_id": lead.project_id,
        "full_name": lead.full_name,
        "email": lead.email,
        "phone": lead.phone,
        "company": lead.company,
        "industry": lead.industry,
        "voivodeship": lead.voivodeship,
        "source": lead.source,
        "campaign_id": lead.campaign_id,
        "assigned_to": lead.assigned_to,
        "stage": lead.stage,
        "score": lead.score,
        "conversion_probability": lead.conversion_probability,
        "notes": lead.notes,
        "tags": lead.tags,
        "follow_up_at": lead.follow_up_at.isoformat() if lead.follow_up_at else None,
        "closed_at": lead.closed_at.isoformat() if lead.closed_at else None,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }
