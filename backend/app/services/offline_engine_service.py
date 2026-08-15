"""Offline engine service for generators, offers, payments and events."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.models import Campaign, EngineEvent, EngineLog, Lead, Offer, Payment, UserProfile
from app.utils.offline import conversion_probability, generate_offer_content, marketing_copy, score_lead, seeded_rng


def log(db: Session, module: str, message: str, level: str = "info"):
    db.add(EngineLog(level=level, module=module, message=message))


def emit_event(db: Session, event_type: str, payload: dict, source: str = "offline"):
    db.add(EngineEvent(event_type=event_type, payload_json=json.dumps(payload, ensure_ascii=False), source=source))


def pick_assignee(db: Session) -> str:
    users = db.query(UserProfile).filter(UserProfile.active == True, UserProfile.role.in_(["agent", "manager"])).all()
    if not users:
        return ""
    counts = {
        user.username: db.query(Lead).filter(
            Lead.assigned_to == user.username,
            Lead.stage.not_in(["wygrany", "przegrany"]),
        ).count()
        for user in users
    }
    return min(counts, key=counts.get)


def generate_campaign(db: Session, name: str, industry: str, budget: float = 0.0, project_id: str = "default") -> Campaign:
    copy = marketing_copy(name, industry)
    campaign = Campaign(
        project_id=project_id,
        name=name,
        description=f"{copy['headline']} | {copy['description']} | CTA: {copy['cta']}",
        source="offline-generator",
        budget=budget,
        target_leads=max(10, int((budget or 1000) / 50)),
        status="aktywna",
    )
    db.add(campaign)
    db.flush()
    emit_event(db, "campaign.generated", {"campaign_id": campaign.id, "name": campaign.name})
    log(db, "campaign-generator", f"Generated campaign {campaign.name}#{campaign.id}")
    return campaign


def generate_leads(db: Session, campaign: Campaign, count: int, industry: str, voivodeship: str) -> list[Lead]:
    created: list[Lead] = []
    existing_for_campaign = db.query(Lead).filter(Lead.campaign_id == campaign.id).count()
    rng = seeded_rng(campaign.name, industry, voivodeship, str(count), str(campaign.id), str(existing_for_campaign))
    for idx in range(count):
        company = f"{industry.title()} Partner {rng.randint(1000, 9999)}"
        email = f"kontakt{rng.randint(100,999)}@{company.lower().replace(' ', '')}.pl"
        phone = f"+48{rng.randint(500000000, 899999999)}"
        lead = Lead(
            project_id=campaign.project_id,
            full_name=f"Opiekun {rng.randint(1, 99)}",
            email=email,
            phone=phone,
            company=company,
            industry=industry,
            voivodeship=voivodeship,
            source="offline-generator",
            campaign_id=campaign.id,
            assigned_to=pick_assignee(db),
            stage="nowy",
            follow_up_at=datetime.utcnow() + timedelta(days=1),
        )
        lead.score = score_lead(lead.email, lead.phone, lead.company, lead.industry, lead.voivodeship)
        lead.conversion_probability = conversion_probability(lead.score, lead.stage)
        db.add(lead)
        created.append(lead)
    db.flush()
    emit_event(db, "leads.generated", {"campaign_id": campaign.id, "count": len(created)})
    log(db, "lead-generator", f"Generated {len(created)} leads for campaign {campaign.id}")
    return created


def generate_offer_for_lead(db: Session, lead: Lead, amount: float | None = None) -> Offer:
    amount = amount if amount is not None else max(299.0, 200 + lead.score * 12)
    offer = Offer(
        lead_id=lead.id,
        title=f"Oferta dla {lead.company or lead.full_name or f'Lead {lead.id}'}",
        amount=round(float(amount), 2),
        content=generate_offer_content(lead.company, lead.industry, float(amount)),
        status="draft",
    )
    db.add(offer)
    db.flush()
    emit_event(db, "offer.generated", {"lead_id": lead.id, "offer_id": offer.id, "amount": offer.amount})
    log(db, "offer-generator", f"Generated offer {offer.id} for lead {lead.id}")
    return offer


def simulate_payment(db: Session, lead_id: int, amount: float, offer_id: int | None = None) -> Payment:
    code = f"OFF-{lead_id}-{int(datetime.utcnow().timestamp())}-{uuid4().hex[:8]}"
    payment = Payment(
        lead_id=lead_id,
        offer_id=offer_id,
        amount=round(float(amount), 2),
        status="confirmed",
        method="offline_transfer",
        confirmation_code=code,
        log="offline simulation: confirmed automatically",
    )
    db.add(payment)
    db.flush()
    emit_event(db, "payment.confirmed", {"payment_id": payment.id, "lead_id": lead_id, "amount": payment.amount})
    log(db, "payment-sim", f"Payment {payment.id} confirmed for lead {lead_id}")
    return payment


def run_sales_automations(db: Session, leads: Iterable[Lead]) -> dict:
    assigned = 0
    followed_up = 0
    closed = 0
    offers = 0
    for lead in leads:
        changed = False
        if not lead.assigned_to:
            lead.assigned_to = pick_assignee(db)
            if lead.assigned_to:
                assigned += 1
                changed = True
        if not lead.follow_up_at and lead.stage not in ["wygrany", "przegrany"]:
            lead.follow_up_at = datetime.utcnow() + timedelta(days=1)
            followed_up += 1
            changed = True
        lead.score = score_lead(lead.email, lead.phone, lead.company, lead.industry, lead.voivodeship)
        lead.conversion_probability = conversion_probability(lead.score, lead.stage)

        if lead.stage == "negocjacje" and lead.conversion_probability >= 0.6:
            exists_offer = db.query(Offer).filter(Offer.lead_id == lead.id).first()
            if not exists_offer:
                generate_offer_for_lead(db, lead)
                offers += 1

        if lead.stage not in ["wygrany", "przegrany"] and lead.conversion_probability < 0.08:
            lead.stage = "przegrany"
            lead.closed_at = datetime.utcnow()
            closed += 1
            changed = True

        if changed:
            emit_event(db, "lead.automation.updated", {"lead_id": lead.id, "stage": lead.stage, "score": lead.score})

    log(db, "sales-automation", f"assigned={assigned}, followups={followed_up}, closed={closed}, offers={offers}")
    return {
        "assigned": assigned,
        "follow_ups": followed_up,
        "closed": closed,
        "offers_generated": offers,
    }
