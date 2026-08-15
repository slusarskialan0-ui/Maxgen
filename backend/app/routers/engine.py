"""Offline engine router for generation, synchronization and self-heal tools."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from app.automations.sales_automation import run_for_all_open_leads
from app.models.models import Campaign, EngineEvent, EngineLog, Lead, Offer, Payment
from app.services.offline_engine_service import generate_campaign, generate_leads, log, emit_event
from app.utils.offline import marketing_copy

router = APIRouter(prefix="/engine", tags=["engine"])


class GeneratorPayload(BaseModel):
    campaign_name: str = "Kampania Offline"
    industry: str = "motoryzacja"
    voivodeship: str = "mazowieckie"
    leads_count: int = 20
    budget: float = 2000.0
    project_id: str = "default"


@router.post("/generate")
def generate_offline_bundle(payload: GeneratorPayload, db: Session = Depends(get_db)):
    campaign = generate_campaign(
        db,
        name=payload.campaign_name,
        industry=payload.industry,
        budget=payload.budget,
        project_id=payload.project_id,
    )
    leads = generate_leads(
        db,
        campaign=campaign,
        count=max(1, min(200, payload.leads_count)),
        industry=payload.industry,
        voivodeship=payload.voivodeship,
    )
    automation_summary = run_for_all_open_leads(db)
    db.commit()
    return {
        "ok": True,
        "campaign_id": campaign.id,
        "generated_leads": len(leads),
        "automations": automation_summary,
    }


@router.get("/marketing-content")
def generate_marketing_content(campaign_name: str = "Kampania Offline", industry: str = "motoryzacja"):
    return marketing_copy(campaign_name, industry)


@router.get("/traffic-dashboard")
def traffic_dashboard(db: Session = Depends(get_db)):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    month = datetime.utcnow().strftime("%Y-%m")
    day_expr = func.strftime("%Y-%m-%d", Lead.created_at)
    month_expr = func.strftime("%Y-%m", Lead.created_at)
    daily = db.query(func.count(Lead.id)).filter(day_expr == today).scalar() or 0
    monthly = db.query(func.count(Lead.id)).filter(month_expr == month).scalar() or 0
    by_source = db.query(Lead.source, func.count(Lead.id)).group_by(Lead.source).all()
    return {
        "daily_traffic": int(daily),
        "monthly_traffic": int(monthly),
        "sources": [{"source": s or "unknown", "count": int(c)} for s, c in by_source],
    }


@router.get("/conversion-dashboard")
def conversion_dashboard(db: Session = Depends(get_db)):
    total = db.query(func.count(Lead.id)).scalar() or 0
    won = db.query(func.count(Lead.id)).filter(Lead.stage == "wygrany").scalar() or 0
    avg_score = db.query(func.coalesce(func.avg(Lead.score), 0.0)).scalar() or 0.0
    avg_prob = db.query(func.coalesce(func.avg(Lead.conversion_probability), 0.0)).scalar() or 0.0
    return {
        "total_leads": int(total),
        "won_leads": int(won),
        "conversion_rate_pct": round((won / total * 100), 2) if total else 0.0,
        "avg_score": round(float(avg_score), 2),
        "avg_conversion_pct": round(float(avg_prob) * 100, 2),
    }


@router.get("/revenue-dashboard")
def revenue_dashboard(db: Session = Depends(get_db)):
    offers_total = db.query(func.coalesce(func.sum(Offer.amount), 0.0)).scalar() or 0.0
    payments_total = db.query(func.coalesce(func.sum(Payment.amount), 0.0)).scalar() or 0.0
    payments_confirmed = db.query(func.count(Payment.id)).filter(Payment.status == "confirmed").scalar() or 0
    payments_failed = db.query(func.count(Payment.id)).filter(Payment.status == "failed").scalar() or 0
    return {
        "offers_amount_total": round(float(offers_total), 2),
        "payments_amount_total": round(float(payments_total), 2),
        "payments_confirmed": int(payments_confirmed),
        "payments_failed": int(payments_failed),
    }


@router.post("/self-heal")
def self_heal(db: Session = Depends(get_db)):
    open_count = db.query(func.count(Lead.id)).filter(Lead.stage.not_in(["wygrany", "przegrany"])).scalar() or 0
    summary = run_for_all_open_leads(db)
    log(db, "self-heal", f"self-heal for {int(open_count)} open leads")
    emit_event(db, "system.self_heal", summary)
    db.commit()
    return {"ok": True, **summary}


@router.get("/events")
def list_events(limit: int = 100, event_type: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(EngineEvent)
    if event_type:
        q = q.filter(EngineEvent.event_type == event_type)
    rows = q.order_by(EngineEvent.created_at.desc()).limit(max(1, min(500, limit))).all()
    return [
        {
            "id": r.id,
            "event_type": r.event_type,
            "payload_json": r.payload_json,
            "source": r.source,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/logs")
def list_logs(limit: int = 100, module: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(EngineLog)
    if module:
        q = q.filter(EngineLog.module == module)
    rows = q.order_by(EngineLog.created_at.desc()).limit(max(1, min(500, limit))).all()
    return [
        {
            "id": r.id,
            "level": r.level,
            "module": r.module,
            "message": r.message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
