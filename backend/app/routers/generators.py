"""Offline lead generators and simulation endpoints."""
import random
from datetime import datetime, timedelta
from typing import Optional

from faker import Faker
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Campaign, Lead
from app.routers.leads import _auto_assign, _compute_conversion, _compute_score, _serialize

router = APIRouter(prefix="/generators", tags=["generators"])

faker = Faker("pl_PL")

INDUSTRIES = [
    "Motoryzacja",
    "Transport",
    "Logistyka",
    "Finanse",
    "Ubezpieczenia",
    "E-commerce",
    "Budownictwo",
    "Serwis flotowy",
]
VOIVODESHIPS = [
    "dolnośląskie",
    "kujawsko-pomorskie",
    "lubelskie",
    "lubuskie",
    "łódzkie",
    "małopolskie",
    "mazowieckie",
    "opolskie",
    "podkarpackie",
    "podlaskie",
    "pomorskie",
    "śląskie",
    "świętokrzyskie",
    "warmińsko-mazurskie",
    "wielkopolskie",
    "zachodniopomorskie",
]
SOURCE_LABELS = {
    "ruch": "ruch organiczny",
    "kampania": "kampania offline",
    "formularz": "formularz papierowy",
    "reklama": "reklama lokalna",
    "social_media": "social media",
    "marketplace": "marketplace",
}
TAG_POOL = [
    "offline",
    "auto",
    "B2B",
    "premium",
    "serwis",
    "flota",
    "dealer",
    "szybki_kontakt",
]
SOURCE_BONUS = {
    "ruch": 7,
    "kampania": 10,
    "formularz": 6,
    "reklama": 8,
    "social_media": 9,
    "marketplace": 12,
}


class ConversionRequest(BaseModel):
    count: int = 5


def _ensure_campaign(db: Session, source: str) -> Campaign:
    campaign = (
        db.query(Campaign)
        .filter(Campaign.source == source)
        .order_by(Campaign.created_at.desc())
        .first()
    )
    if campaign:
        return campaign
    campaign = Campaign(
        name=f"Kampania {SOURCE_LABELS.get(source, source)}",
        description=f"Automatycznie utworzona kampania dla źródła {source}.",
        source=source,
        status="aktywna",
        budget=round(random.uniform(3000, 20000), 2),
        target_leads=random.randint(50, 300),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def _enhanced_score(lead: Lead) -> float:
    score = _compute_score(lead)
    score += SOURCE_BONUS.get(lead.source, 5)
    if lead.assigned_to:
        score += 4
    if lead.tags:
        score += min(10, len([t for t in lead.tags.split(",") if t.strip()]) * 2)
    if lead.notes:
        score += min(8, len(lead.notes) / 30)
    if lead.email and lead.email.endswith(".pl"):
        score += 3
    if lead.stage == "kontakt":
        score += 6
    elif lead.stage == "negocjacje":
        score += 12
    return round(min(max(score, 0), 100), 1)


def _build_lead(source: str, campaign: Campaign, db: Session) -> Lead:
    first = faker.first_name()
    last = faker.last_name()
    company = faker.company()
    industry = random.choice(INDUSTRIES)
    tags = ",".join(sorted(set(random.sample(TAG_POOL, k=random.randint(2, 4)))))
    notes = (
        f"Lead pozyskany przez {SOURCE_LABELS.get(source, source)}. "
        f"Zainteresowanie: {random.choice(['leasingiem', 'zakupem floty', 'serwisem aut', 'ubezpieczeniem pojazdów'])}."
    )
    lead = Lead(
        full_name=f"{first} {last}",
        email=faker.unique.email(),
        phone=faker.phone_number(),
        company=company,
        industry=industry,
        voivodeship=random.choice(VOIVODESHIPS),
        source=source,
        campaign_id=campaign.id,
        assigned_to=_auto_assign(db),
        stage=random.choices(["nowy", "kontakt", "negocjacje"], weights=[70, 20, 10], k=1)[0],
        notes=notes,
        tags=tags,
        follow_up_at=datetime.utcnow() + timedelta(days=random.randint(1, 7)),
    )
    lead.score = _enhanced_score(lead)
    lead.conversion_probability = _compute_conversion(lead.score, lead.stage)
    return lead


def _generate_source(source: str, db: Session, count: int = 20) -> dict:
    campaign = _ensure_campaign(db, source)
    leads = [_build_lead(source, campaign, db) for _ in range(count)]
    db.add_all(leads)
    db.commit()
    for lead in leads:
        db.refresh(lead)
    campaign.current_leads = (campaign.current_leads or 0) + count
    db.commit()
    return {
        "ok": True,
        "source": source,
        "campaign_id": campaign.id,
        "added": count,
        "items": [_serialize(lead) for lead in leads],
    }


def _run_all_sources(db: Session) -> dict:
    results = []
    total = 0
    for source in SOURCE_LABELS:
        result = _generate_source(source, db)
        total += result["added"]
        results.append({"source": result["source"], "campaign_id": result["campaign_id"], "added": result["added"]})
    return {"ok": True, "added": total, "results": results}


@router.get("/traffic")
def generate_traffic(db: Session = Depends(get_db)):
    return _generate_source("ruch", db)


@router.get("/campaign")
def generate_campaign(db: Session = Depends(get_db)):
    return _generate_source("kampania", db)


@router.get("/forms")
def generate_forms(db: Session = Depends(get_db)):
    return _generate_source("formularz", db)


@router.get("/ads")
def generate_ads(db: Session = Depends(get_db)):
    return _generate_source("reklama", db)


@router.get("/social")
def generate_social(db: Session = Depends(get_db)):
    return _generate_source("social_media", db)


@router.get("/marketplace")
def generate_marketplace(db: Session = Depends(get_db)):
    return _generate_source("marketplace", db)


@router.post("/run-all")
def run_all_generators(db: Session = Depends(get_db)):
    return _run_all_sources(db)


@router.get("/behaviors")
def generate_behaviors(limit: int = 20, db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
    items = []
    for lead in leads:
        pages_visited = max(1, min(12, int((lead.score or 0) / 12) + random.randint(0, 3)))
        dwell_time = max(15, int((lead.conversion_probability or 0) * 300) + random.randint(20, 180))
        clickthrough = round(min(0.95, 0.05 + (lead.score or 0) / 120 + random.uniform(0.01, 0.2)), 3)
        items.append({
            "lead_id": lead.id,
            "full_name": lead.full_name,
            "company": lead.company,
            "clickthrough": clickthrough,
            "dwell_time": dwell_time,
            "pages_visited": pages_visited,
            "source": lead.source,
        })
    return {"items": items, "count": len(items)}


@router.get("/scoring")
def offline_scoring(db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.stage.not_in(["wygrany", "przegrany"])).order_by(Lead.created_at.desc()).all()
    items = []
    for lead in leads:
        lead.score = _enhanced_score(lead)
        lead.conversion_probability = _compute_conversion(lead.score, lead.stage)
        items.append(_serialize(lead))
    db.commit()
    items.sort(key=lambda item: item["conversion_probability"], reverse=True)
    return {"count": len(items), "items": items}


@router.post("/conversions")
def generate_conversions(payload: Optional[ConversionRequest] = None, db: Session = Depends(get_db)):
    count = max(1, min((payload.count if payload else 5), 20))
    leads = (
        db.query(Lead)
        .filter(Lead.stage.not_in(["wygrany", "przegrany"]))
        .order_by(Lead.conversion_probability.desc(), Lead.score.desc())
        .limit(count)
        .all()
    )
    events = []
    for lead in leads:
        lead.stage = "wygrany"
        lead.closed_at = datetime.utcnow()
        lead.conversion_probability = 1.0
        lead.notes = (lead.notes or "") + f"\nKonwersja testowa wygenerowana: {datetime.utcnow().isoformat()}."
        events.append({
            "lead_id": lead.id,
            "company": lead.company,
            "event": "conversion_test",
            "value_pln": round(lead.score * random.uniform(80, 180), 2),
            "converted_at": lead.closed_at.isoformat(),
        })
    db.commit()
    return {"ok": True, "converted": len(events), "items": events}
