from __future__ import annotations

import json
import os
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.data.geography import DEFAULT_INDUSTRIES, VOIVODESHIPS
from app.models.models import Automation, Campaign, Lead, Log, Offer, Payment, User
from app.sources.sources import ALL_SOURCES
from database import get_db

router = APIRouter(prefix="/auto", tags=["auto"])
BASE_DIR = Path(__file__).resolve().parents[2]
BACKUP_DIR = Path(os.getenv("AUTO_BACKUP_DIR", str(BASE_DIR / "runtime_backups")))


class LeadGenerationPayload(BaseModel):
    voivodeship: str = "mazowieckie"
    industries: list[str] = []
    limit: int = 18


class ImportPayload(BaseModel):
    leads: list[dict] = []
    campaigns: list[dict] = []
    offers: list[dict] = []
    payments: list[dict] = []


DEFAULT_USERS = [
    {"full_name": "Anna Sprzedaż", "email": "anna.sprzedaz@offline.local", "role": "sales", "territory": "centrum", "capacity": 35},
    {"full_name": "Marek Follow-up", "email": "marek.followup@offline.local", "role": "follow_up", "territory": "poludnie", "capacity": 30},
    {"full_name": "Julia Kampanie", "email": "julia.kampanie@offline.local", "role": "marketing", "territory": "polnoc", "capacity": 28},
]
CAMPAIGN_CHANNELS = ["sms", "email", "telefon", "remarketing-offline"]
PAYMENT_STATUSES = ["confirmed", "pending", "failed"]


def _now() -> datetime:
    return datetime.utcnow()


def _log(db: Session, category: str, message: str, metadata: str = "") -> None:
    db.add(Log(category=category, message=message, metadata_text=metadata))


def _ensure_users(db: Session) -> list[User]:
    users = db.query(User).all()
    if users:
        return users
    for payload in DEFAULT_USERS:
        db.add(User(**payload))
    db.commit()
    return db.query(User).order_by(User.id.asc()).all()


def _default_industries() -> list[str]:
    return [item["name"] for item in DEFAULT_INDUSTRIES[:6]]


def _score_profile(profile) -> tuple[int, int]:
    traffic = 35
    traffic += 20 if profile.website else 0
    traffic += 20 if profile.phone else 0
    traffic += 15 if profile.email else 0
    traffic += 10 if profile.source_type in {"katalog", "rejestr", "mapa"} else 4
    score = min(99, traffic + (8 if "auto" in profile.industry.lower() else 3))
    return min(100, traffic), score


def _pick_owner(users: list[User], workload: Counter) -> Optional[User]:
    def _load(user: User):
        return workload.get(user.id, 0) / max(user.capacity or 1, 1)
    return sorted(users, key=_load)[0] if users else None


def _get_or_create_automation(db: Session, automation_type: str) -> Automation:
    row = db.query(Automation).filter_by(automation_type=automation_type).first()
    if row:
        return row
    row = Automation(automation_type=automation_type, status="idle", summary="")
    db.add(row)
    db.flush()
    return row


def _lead_payload(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "company_name": lead.company_name,
        "industry": lead.industry,
        "source_type": lead.source_type,
        "voivodeship": lead.voivodeship,
        "city": lead.city,
        "email": lead.email,
        "phone": lead.phone,
        "website": lead.website,
        "traffic_score": lead.traffic_score,
        "offline_ai_score": lead.offline_ai_score,
        "qualification_status": lead.qualification_status,
        "funnel_stage": lead.funnel_stage,
        "owner_id": lead.owner_id,
        "campaign_name": lead.campaign_name,
        "notes": lead.notes,
        "generated_content": lead.generated_content,
        "follow_up_due_at": lead.follow_up_due_at.isoformat() if lead.follow_up_due_at else None,
        "closed_at": lead.closed_at.isoformat() if lead.closed_at else None,
        "is_closed": lead.is_closed,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


def _campaign_payload(campaign: Campaign) -> dict:
    return {
        "id": campaign.id,
        "name": campaign.name,
        "channel": campaign.channel,
        "audience": campaign.audience,
        "description": campaign.description,
        "cta": campaign.cta,
        "ad_copy": campaign.ad_copy,
        "traffic_goal": campaign.traffic_goal,
        "status": campaign.status,
        "generated_at": campaign.generated_at.isoformat() if campaign.generated_at else None,
    }


def _offer_payload(offer: Offer) -> dict:
    return {
        "id": offer.id,
        "lead_id": offer.lead_id,
        "title": offer.title,
        "summary": offer.summary,
        "price": float(offer.price or 0),
        "status": offer.status,
        "sales_copy": offer.sales_copy,
        "created_at": offer.created_at.isoformat() if offer.created_at else None,
    }


def _payment_payload(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "lead_id": payment.lead_id,
        "offer_id": payment.offer_id,
        "amount": float(payment.amount or 0),
        "status": payment.status,
        "method": payment.method,
        "confirmation_code": payment.confirmation_code,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }


def _export_payload(db: Session) -> dict:
    return {
        'exported_at': _now().isoformat(),
        'leads': [_lead_payload(row) for row in db.query(Lead).all()],
        'campaigns': [_campaign_payload(row) for row in db.query(Campaign).all()],
        'offers': [_offer_payload(row) for row in db.query(Offer).all()],
        'payments': [_payment_payload(row) for row in db.query(Payment).all()],
    }


@router.post('/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    users = _ensure_users(db)
    for automation_type in ['lead_generation', 'sales', 'campaigns', 'payments', 'sync', 'recovery']:
        _get_or_create_automation(db, automation_type)
    if db.query(Campaign).count() == 0:
        for idx, industry in enumerate(_default_industries()[:3], start=1):
            db.add(Campaign(
                name=f'Offline Launch {idx} - {industry.title()}',
                channel=CAMPAIGN_CHANNELS[(idx - 1) % len(CAMPAIGN_CHANNELS)],
                audience=f'Firmy {industry} w Polsce',
                description=f'Lokalna kampania generowania ruchu dla branży {industry}.',
                cta='Umów audyt offline i odbierz ofertę w 24h.',
                ad_copy=f'Więcej leadów dla branży {industry} bez API i bez zewnętrznych usług.',
                traffic_goal=120 + idx * 30,
                status='active',
            ))
    db.commit()
    _log(db, 'bootstrap', 'Offline automation bootstrap completed', f'users={len(users)}')
    db.commit()
    return {'status': 'ok', 'users': len(users), 'campaigns': db.query(Campaign).count()}


@router.post('/leads/generate')
def generate_leads(payload: LeadGenerationPayload, db: Session = Depends(get_db)):
    voivodeship = payload.voivodeship if payload.voivodeship in VOIVODESHIPS else 'mazowieckie'
    industries = payload.industries or _default_industries()
    limit = max(3, min(payload.limit, 48))
    _ensure_users(db)
    automation = _get_or_create_automation(db, 'lead_generation')
    automation.status = 'running'
    automation.last_run_at = _now()

    profiles = []
    source_cycle = list(ALL_SOURCES)
    for source in source_cycle:
        profiles.extend(source.fetch(voivodeship, industries)[: max(2, limit // max(len(source_cycle), 1))])
    industry_key = "-".join(sorted(industries))
    random.Random(f'{voivodeship}-{industry_key}-{limit}').shuffle(profiles)
    profiles = profiles[:limit]

    created = []
    for index, profile in enumerate(profiles, start=1):
        traffic_score, offline_score = _score_profile(profile)
        lead = Lead(
            company_name=profile.company_name,
            industry=profile.industry,
            source_type=profile.source_type,
            voivodeship=profile.voivodeship,
            city=profile.city,
            email=profile.email,
            phone=profile.phone,
            website=profile.website,
            traffic_score=traffic_score,
            offline_ai_score=offline_score,
            qualification_status='new',
            funnel_stage='generated',
            campaign_name=f'Offline {profile.industry.title()} {profile.voivodeship.title()}',
            generated_content=f'Offline lead dla {profile.company_name}: audyt sprzedaży, oferta i follow-up bez integracji zewnętrznych.',
            notes=f'Źródło: {profile.source_detail}. Ruch lokalny: {traffic_score}/100. Lead #{index}.',
        )
        db.add(lead)
        created.append(lead)

    automation.status = 'completed'
    automation.items_processed = len(created)
    automation.summary = f'Generated {len(created)} leads for {voivodeship}'
    automation.recovery_action = 'Rerun generator or restore latest backup'
    _log(db, 'lead_generation', f'Generated {len(created)} offline leads', voivodeship)
    db.commit()
    return {'status': 'ok', 'created': len(created), 'voivodeship': voivodeship, 'industries': industries}


@router.get('/leads')
def list_leads(limit: int = 25, db: Session = Depends(get_db)):
    rows = db.query(Lead).order_by(Lead.created_at.desc(), Lead.id.desc()).limit(max(1, min(limit, 100))).all()
    return {'total': db.query(Lead).count(), 'items': [_lead_payload(row) for row in rows]}


@router.post('/sales/run')
def run_sales_automation(db: Session = Depends(get_db)):
    users = _ensure_users(db)
    automation = _get_or_create_automation(db, 'sales')
    automation.status = 'running'
    automation.last_run_at = _now()
    leads = db.query(Lead).filter(Lead.is_closed.is_(False)).order_by(Lead.offline_ai_score.desc(), Lead.id.asc()).all()
    workload = Counter(owner_id for (owner_id,) in db.query(Lead.owner_id).filter(Lead.owner_id.isnot(None)).all())
    existing_offer_lead_ids = {lead_id for (lead_id,) in db.query(Offer.lead_id).filter(Offer.lead_id.isnot(None)).all()}
    processed = 0
    won = 0
    lost = 0
    for lead in leads:
        owner = _pick_owner(users, workload)
        if owner and not lead.owner_id:
            lead.owner_id = owner.id
            workload[owner.id] += 1
        if lead.offline_ai_score >= 85:
            lead.qualification_status = 'hot'
            lead.funnel_stage = 'proposal'
        elif lead.offline_ai_score >= 65:
            lead.qualification_status = 'warm'
            lead.funnel_stage = 'follow_up'
        else:
            lead.qualification_status = 'cold'
            lead.funnel_stage = 'nurture'
        lead.follow_up_due_at = _now() + timedelta(days=2 if lead.qualification_status == 'hot' else 4)
        lead.generated_content = (
            f'Oferta offline dla {lead.company_name}: szybki audyt, wdrożenie kampanii, follow-up i raport przychodów. '
            f'Priorytet: {lead.qualification_status}. Opiekun: {lead.owner_id or "brak"}.'
        )
        if lead.id not in existing_offer_lead_ids:
            price = 1490.0 + lead.offline_ai_score * 22
            db.add(Offer(
                lead_id=lead.id,
                title=f'Pakiet AUTO sprzedaż - {lead.company_name}',
                summary=f'Lejek sprzedaży, kampania i follow-up dla branży {lead.industry}.',
                price=round(price, 2),
                status='generated',
                sales_copy=f'Uruchomimy lokalny system leadów dla {lead.company_name} bez API, z pełnym offline follow-up.',
            ))
            existing_offer_lead_ids.add(lead.id)
        if lead.offline_ai_score >= 92:
            lead.funnel_stage = 'closed_won'
            lead.qualification_status = 'won'
            lead.is_closed = True
            lead.closed_at = _now()
            won += 1
        elif lead.offline_ai_score < 55:
            lead.funnel_stage = 'closed_lost'
            lead.qualification_status = 'lost'
            lead.is_closed = True
            lead.closed_at = _now()
            lost += 1
        processed += 1
    automation.status = 'completed'
    automation.items_processed = processed
    automation.summary = f'Qualified {processed} leads, won={won}, lost={lost}'
    automation.recovery_action = 'Regenerate offers or re-open lost leads after import'
    _log(db, 'sales', f'Sales automation processed {processed} leads', f'won={won};lost={lost}')
    db.commit()
    return {'status': 'ok', 'processed': processed, 'won': won, 'lost': lost}


@router.get('/sales/pipeline')
def sales_pipeline(db: Session = Depends(get_db)):
    rows = db.query(Lead.funnel_stage).all()
    stages = Counter(stage or 'generated' for stage, in rows)
    owners = {user.id: user.full_name for user in db.query(User).all()}
    lead_rows = db.query(Lead).order_by(Lead.offline_ai_score.desc(), Lead.id.desc()).limit(12).all()
    return {
        'stages': stages,
        'owners': owners,
        'items': [_lead_payload(row) for row in lead_rows],
    }


@router.post('/campaigns/generate')
def generate_campaigns(db: Session = Depends(get_db)):
    automation = _get_or_create_automation(db, 'campaigns')
    automation.status = 'running'
    automation.last_run_at = _now()
    industries = [industry for (industry,) in db.query(Lead.industry).all() if industry] or _default_industries()
    top_industries = [name for name, _ in Counter(industries).most_common(4)]
    created = []
    for idx, industry in enumerate(top_industries, start=1):
        name = f'Campaign {industry.title()} {idx}'
        existing = db.query(Campaign).filter_by(name=name).first()
        if existing:
            created.append(existing)
            continue
        campaign = Campaign(
            name=name,
            channel=CAMPAIGN_CHANNELS[(idx - 1) % len(CAMPAIGN_CHANNELS)],
            audience=f'Firmy {industry} z lead score > 65',
            description=f'Offline kampania wzmacniająca ruch lokalny i konwersję dla branży {industry}.',
            cta='Zarezerwuj wdrożenie i odbierz demo oferty offline.',
            ad_copy=f'Generujemy leady i domykamy sprzedaż dla firm {industry} całkowicie lokalnie — bez kluczy API.',
            traffic_goal=160 + idx * 40,
            status='active',
        )
        db.add(campaign)
        created.append(campaign)
    automation.status = 'completed'
    automation.items_processed = len(created)
    automation.summary = f'Generated {len(created)} offline campaigns'
    automation.recovery_action = 'Refresh campaigns or restore export payload'
    _log(db, 'campaigns', f'Generated {len(created)} campaigns')
    db.commit()
    return {'status': 'ok', 'created': len(created)}


@router.get('/campaigns')
def list_campaigns(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.query(Campaign).order_by(Campaign.generated_at.desc(), Campaign.id.desc()).limit(max(1, min(limit, 100))).all()
    return {'total': db.query(Campaign).count(), 'items': [_campaign_payload(row) for row in rows]}


@router.get('/offers')
def list_offers(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.query(Offer).order_by(Offer.created_at.desc(), Offer.id.desc()).limit(max(1, min(limit, 100))).all()
    return {'total': db.query(Offer).count(), 'items': [_offer_payload(row) for row in rows]}


@router.post('/payments/simulate')
def simulate_payments(db: Session = Depends(get_db)):
    automation = _get_or_create_automation(db, 'payments')
    automation.status = 'running'
    automation.last_run_at = _now()
    offers = db.query(Offer).order_by(Offer.id.asc()).all()
    created = 0
    for idx, offer in enumerate(offers, start=1):
        if db.query(Payment).filter_by(offer_id=offer.id).first():
            continue
        status = PAYMENT_STATUSES[0 if idx % 3 == 1 else 1 if idx % 3 == 2 else 2]
        payment = Payment(
            lead_id=offer.lead_id,
            offer_id=offer.id,
            amount=offer.price,
            status=status,
            method='offline_transfer' if idx % 2 else 'cash_collection',
            confirmation_code=f'OFF-{offer.id:04d}-{idx:03d}',
            paid_at=_now() if status == 'confirmed' else None,
        )
        db.add(payment)
        created += 1
    automation.status = 'completed'
    automation.items_processed = created
    automation.summary = f'Simulated {created} offline payments'
    automation.recovery_action = 'Replay simulation after import or restore backup'
    _log(db, 'payments', f'Simulated {created} offline payments')
    db.commit()
    return {'status': 'ok', 'created': created}


@router.get('/payments')
def list_payments(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.query(Payment).order_by(Payment.created_at.desc(), Payment.id.desc()).limit(max(1, min(limit, 100))).all()
    return {'total': db.query(Payment).count(), 'items': [_payment_payload(row) for row in rows]}


@router.get('/dashboard/conversion')
def conversion_dashboard(db: Session = Depends(get_db)):
    total = db.query(Lead).count()
    qualified = db.query(Lead).filter(Lead.qualification_status.in_(['hot', 'warm', 'won'])).count()
    offers = db.query(Offer).count()
    won = db.query(Lead).filter(Lead.qualification_status == 'won').count()
    confirmed = db.query(Payment).filter(Payment.status == 'confirmed').count()
    def _pct(part: int, whole: int) -> float:
        return round((part / whole) * 100, 2) if whole else 0.0
    return {
        'total_leads': total,
        'qualified_leads': qualified,
        'offers_generated': offers,
        'won_leads': won,
        'confirmed_payments': confirmed,
        'qualification_rate_pct': _pct(qualified, total),
        'offer_rate_pct': _pct(offers, total),
        'close_rate_pct': _pct(won, total),
        'payment_success_rate_pct': _pct(confirmed, max(offers, 1)),
    }


@router.get('/dashboard/revenue')
def revenue_dashboard(db: Session = Depends(get_db)):
    payments = db.query(Payment).all()
    monthly = defaultdict(float)
    for payment in payments:
        if payment.paid_at:
            monthly[payment.paid_at.strftime('%Y-%m')] += float(payment.amount or 0)
    total_revenue = round(sum(float(payment.amount or 0) for payment in payments if payment.status == 'confirmed'), 2)
    pipeline_value = round(sum(float(offer.price or 0) for offer in db.query(Offer).all()), 2)
    return {
        'total_revenue': total_revenue,
        'pipeline_value': pipeline_value,
        'pending_revenue': round(sum(float(payment.amount or 0) for payment in payments if payment.status == 'pending'), 2),
        'failed_revenue': round(sum(float(payment.amount or 0) for payment in payments if payment.status == 'failed'), 2),
        'by_month': [{'month': month, 'revenue': round(value, 2)} for month, value in sorted(monthly.items())],
    }


@router.get('/automations')
def list_automations(db: Session = Depends(get_db)):
    rows = db.query(Automation).order_by(Automation.automation_type.asc()).all()
    logs = db.query(Log).order_by(Log.created_at.desc(), Log.id.desc()).limit(15).all()
    return {
        'automations': [
            {
                'id': row.id,
                'automation_type': row.automation_type,
                'status': row.status,
                'items_processed': row.items_processed,
                'summary': row.summary,
                'recovery_action': row.recovery_action,
                'last_run_at': row.last_run_at.isoformat() if row.last_run_at else None,
            }
            for row in rows
        ],
        'logs': [
            {
                'id': log.id,
                'category': log.category,
                'message': log.message,
                'metadata': log.metadata_text,
                'created_at': log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.post('/sync/export')
def export_data(db: Session = Depends(get_db)):
    payload = _export_payload(db)
    automation = _get_or_create_automation(db, 'sync')
    automation.status = 'completed'
    automation.items_processed = sum(len(payload[key]) for key in ['leads', 'campaigns', 'offers', 'payments'])
    automation.summary = 'Exported offline snapshot'
    automation.recovery_action = 'Import the exported payload or use backup restore'
    _log(db, 'sync', 'Offline export prepared')
    db.commit()
    return payload


@router.post('/sync/import')
def import_data(payload: ImportPayload, db: Session = Depends(get_db)):
    imported = {'leads': 0, 'campaigns': 0, 'offers': 0, 'payments': 0}
    for lead in payload.leads:
        if not lead.get('company_name'):
            continue
        db.add(Lead(
            company_name=lead['company_name'],
            industry=lead.get('industry', ''),
            source_type=lead.get('source_type', 'import'),
            voivodeship=lead.get('voivodeship', ''),
            city=lead.get('city', ''),
            email=lead.get('email', ''),
            phone=lead.get('phone', ''),
            website=lead.get('website', ''),
            traffic_score=int(lead.get('traffic_score', 0) or 0),
            offline_ai_score=int(lead.get('offline_ai_score', 0) or 0),
            qualification_status=lead.get('qualification_status', 'imported'),
            funnel_stage=lead.get('funnel_stage', 'imported'),
            campaign_name=lead.get('campaign_name', ''),
            notes=lead.get('notes', ''),
            generated_content=lead.get('generated_content', ''),
        ))
        imported['leads'] += 1
    for campaign in payload.campaigns:
        if campaign.get('name') and not db.query(Campaign).filter_by(name=campaign['name']).first():
            db.add(Campaign(
                name=campaign['name'],
                channel=campaign.get('channel', 'import'),
                audience=campaign.get('audience', ''),
                description=campaign.get('description', ''),
                cta=campaign.get('cta', ''),
                ad_copy=campaign.get('ad_copy', ''),
                traffic_goal=int(campaign.get('traffic_goal', 0) or 0),
                status=campaign.get('status', 'imported'),
            ))
            imported['campaigns'] += 1
    for offer in payload.offers:
        if offer.get('title'):
            db.add(Offer(
                lead_id=offer.get('lead_id'),
                title=offer['title'],
                summary=offer.get('summary', ''),
                price=float(offer.get('price', 0) or 0),
                status=offer.get('status', 'imported'),
                sales_copy=offer.get('sales_copy', ''),
            ))
            imported['offers'] += 1
    for payment in payload.payments:
        db.add(Payment(
            lead_id=payment.get('lead_id'),
            offer_id=payment.get('offer_id'),
            amount=float(payment.get('amount', 0) or 0),
            status=payment.get('status', 'pending'),
            method=payment.get('method', 'import'),
            confirmation_code=payment.get('confirmation_code', 'IMPORTED'),
            paid_at=_now() if payment.get('status') == 'confirmed' else None,
        ))
        imported['payments'] += 1
    automation = _get_or_create_automation(db, 'sync')
    automation.status = 'completed'
    automation.items_processed = sum(imported.values())
    automation.summary = 'Imported offline snapshot'
    automation.recovery_action = 'Run export again after validation'
    _log(db, 'sync', 'Offline import completed', json.dumps(imported))
    db.commit()
    return {'status': 'ok', 'imported': imported}


@router.post('/sync/backup')
def backup_snapshot(db: Session = Depends(get_db)):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    payload = _export_payload(db)
    filename = BACKUP_DIR / f'backup-{_now().strftime("%Y%m%d-%H%M%S")}.json'
    filename.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    automation = _get_or_create_automation(db, 'sync')
    automation.status = 'completed'
    automation.items_processed = sum(len(payload[key]) for key in ['leads', 'campaigns', 'offers', 'payments'])
    automation.summary = f'Backup written to {filename.name}'
    automation.recovery_action = 'Import the exported payload or use this backup file for recovery'
    _log(db, 'backup', 'Offline backup created', filename.name)
    db.commit()
    return {'status': 'ok', 'file': str(filename), 'records': {key: len(payload[key]) for key in ['leads', 'campaigns', 'offers', 'payments']}}


@router.post('/sync/recovery')
def recover_latest_backup(db: Session = Depends(get_db)):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = sorted(BACKUP_DIR.glob('backup-*.json'))
    automation = _get_or_create_automation(db, 'recovery')
    automation.last_run_at = _now()
    if not backups:
        automation.status = 'idle'
        automation.summary = 'No backup available for recovery'
        automation.recovery_action = 'Create backup first'
        db.commit()
        return {'status': 'idle', 'message': 'No backup available'}
    latest = backups[-1]
    payload = json.loads(latest.read_text())
    automation.status = 'completed'
    automation.items_processed = sum(len(payload.get(key, [])) for key in ['leads', 'campaigns', 'offers', 'payments'])
    automation.summary = f'Latest backup verified: {latest.name}'
    automation.recovery_action = 'Use import endpoint with the verified payload to restore data'
    _log(db, 'recovery', 'Verified latest backup', latest.name)
    db.commit()
    return {'status': 'ok', 'latest_backup': latest.name, 'records': {key: len(payload.get(key, [])) for key in ['leads', 'campaigns', 'offers', 'payments']}}


@router.get('/overview')
def overview(db: Session = Depends(get_db)):
    return {
        'counts': {
            'users': db.query(User).count(),
            'leads': db.query(Lead).count(),
            'campaigns': db.query(Campaign).count(),
            'offers': db.query(Offer).count(),
            'payments': db.query(Payment).count(),
            'logs': db.query(Log).count(),
            'automations': db.query(Automation).count(),
        },
        'conversion': conversion_dashboard(db),
        'revenue': revenue_dashboard(db),
        'sales': sales_pipeline(db),
        'campaigns': list_campaigns(6, db),
        'offers': list_offers(6, db),
        'payments': list_payments(6, db),
        'automations': list_automations(db),
    }
