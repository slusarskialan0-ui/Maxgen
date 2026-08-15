"""Auto-pipeline: orchestrates all data sources and writes results to DB."""

from __future__ import annotations

import concurrent.futures
import json
import logging
import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.models import (
    AcquisitionLog,
    Automation,
    B2BLead,
    Client,
    Location,
    Order,
    VoivodeshipStatus,
)
from app.pipeline.circuit_breaker import source_circuit_breaker
from app.pipeline.recovery import record_source_failure, record_source_success
from app.pipeline.retry_handler import SOURCE_TIMEOUT
from app.sources import ALL_SOURCES, CompanyProfile, validate_email, validate_phone
from app.sources.b2b_sources import B2BLeadCandidate, CurlCffiB2BSource, build_sources
from app.data.geography import ORDER_TEMPLATES

logger = logging.getLogger(__name__)


def _dedup(profiles: list[CompanyProfile]) -> list[CompanyProfile]:
    seen = set()
    result = []
    for p in profiles:
        key = (p.company_name.lower().strip(), p.voivodeship, p.industry)
        if key not in seen:
            seen.add(key)
            result.append(p)
    return result


def _validate(profile: CompanyProfile) -> bool:
    if not profile.company_name or not profile.company_name.strip():
        return False
    if profile.email and not validate_email(profile.email):
        profile.email = ""
    if profile.phone and not validate_phone(profile.phone):
        profile.phone = ""
    return True


def _fetch_source(source, voivodeship: str, industries: list[str]):
    source_key = source.source_type
    if source_circuit_breaker.is_open(source_key):
        wait = source_circuit_breaker.remaining_open_seconds(source_key)
        record_source_failure(source_key, f"circuit_open:{wait}s")
        return source_key, []

    try:
        profiles = source.fetch(voivodeship, industries)
        source_circuit_breaker.record_success(source_key)
        record_source_success(source.source_type, len(profiles))
        return source.source_type, profiles
    except Exception as exc:
        tripped = source_circuit_breaker.record_failure(source_key)
        err = f"{exc}"
        if tripped:
            err = f"circuit_open:{err}"
        record_source_failure(source.source_type, err)
        return source.source_type, []


def run_pipeline(voivodeship: str, industries: list[str], db: Session) -> dict:
    """Run the full acquisition pipeline for given voivodeship + industries."""
    vs = db.query(VoivodeshipStatus).filter_by(voivodeship=voivodeship).first()
    if vs:
        vs.status = "w_trakcie"
        db.commit()

    logs = []
    all_profiles = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(_fetch_source, src, voivodeship, industries): src for src in ALL_SOURCES}
        for future in concurrent.futures.as_completed(futures, timeout=SOURCE_TIMEOUT * len(ALL_SOURCES)):
            source_type, profiles = future.result()
            found = len(profiles)
            logs.append((source_type, found, profiles))
            all_profiles.extend(profiles)

    all_profiles = _dedup(all_profiles)
    accepted = 0
    rejected = 0

    for profile in all_profiles:
        if not _validate(profile):
            rejected += 1
            continue

        loc = db.query(Location).filter_by(
            voivodeship=profile.voivodeship,
            city=profile.city,
            county=profile.county,
        ).first()
        if not loc:
            loc = Location(
                voivodeship=profile.voivodeship,
                county=profile.county,
                city=profile.city,
            )
            db.add(loc)
            db.flush()

        client = Client(
            company_name=profile.company_name,
            industry=profile.industry,
            voivodeship=profile.voivodeship,
            county=profile.county,
            city=profile.city,
            email=profile.email,
            phone=profile.phone,
            website=profile.website,
            source_type=profile.source_type,
            source_detail=profile.source_detail,
            acquired_at=profile.acquired_at,
            status="nowy",
            location_id=loc.id,
        )
        db.add(client)
        db.flush()

        tmpl = ORDER_TEMPLATES.get(profile.industry, (
            f"Pozyskanie klienta – {profile.industry}",
            f"Propozycja współpracy dla firmy z branży {profile.industry}.",
        ))
        order = Order(
            client_id=client.id,
            title=tmpl[0],
            description=f"{tmpl[1]} Lokalizacja: {profile.city}, {profile.voivodeship}.",
            value=round(random.uniform(500, 15000), 2),
            status="nowe",
            created_at=datetime.now(timezone.utc),
        )
        db.add(order)
        accepted += 1

    db.commit()
    _trigger_automations(db, "new_lead")

    for source_type, found, profiles in logs:
        src_accepted = len([p for p in profiles if _validate(p)])
        log = AcquisitionLog(
            voivodeship=voivodeship,
            industries=",".join(industries),
            source_type=source_type,
            found=found,
            accepted=src_accepted,
            rejected=found - src_accepted,
        )
        db.add(log)

    if vs:
        vs.status = "zakonczone"
        vs.last_scan = datetime.now(timezone.utc)
        vs.clients_count = db.query(Client).filter_by(voivodeship=voivodeship).count()
        vs.orders_count = db.query(Order).join(Client).filter(Client.voivodeship == voivodeship).count()
    db.commit()

    return {
        "voivodeship": voivodeship,
        "industries": industries,
        "total_found": len(all_profiles) + rejected,
        "accepted": accepted,
        "rejected": rejected,
        "sources": [{"source_type": st, "found": f} for st, f, _ in logs],
    }


def run_b2b_pipeline(db: Session) -> dict:
    """Run B2B listing scan and persist evaluated leads."""
    sources = build_sources()
    if not sources:
        return {"found": 0, "saved": 0, "alerts": 0, "sources": []}

    found = 0
    saved = 0
    alerts = 0
    source_stats: list[dict] = []

    for source in sources:
        scanned = _scan_source(source)
        found += len(scanned)
        src_saved = 0
        src_alerts = 0
        for item in scanned:
            exists = db.query(B2BLead).filter(B2BLead.direct_link == item.direct_link).first()
            if exists:
                continue
            row = B2BLead(
                source_name=item.source_name,
                external_id=item.external_id,
                title=item.title,
                budget_pln=item.budget_pln,
                vat_required=item.vat_required,
                description=item.description,
                contact_phone=item.contact_phone,
                contact_email=item.contact_email,
                location=item.location,
                work_mode=item.work_mode,
                direct_link=item.direct_link,
                lead_score=item.lead_score,
                raw_payload=json.dumps(item.raw_payload, ensure_ascii=False),
            )
            db.add(row)
            src_saved += 1
            if item.lead_score >= 65:
                from app.services.telegram import telegram_service

                telegram_service.send_lead_alert(item)
                alerts += 1
                src_alerts += 1

        db.commit()
        saved += src_saved
        source_stats.append(
            {
                "source": source.source_name,
                "found": len(scanned),
                "saved": src_saved,
                "alerts": src_alerts,
            }
        )

    return {"found": found, "saved": saved, "alerts": alerts, "sources": source_stats}


def analyze_listing_url(url: str) -> dict:
    """Fetch and score a single listing link for Telegram link pastes."""
    source = CurlCffiB2BSource(source_name="manual_link", endpoints=[url])
    leads = source.fetch_from_url(url)
    if not leads:
        raise ValueError("Nie udało się znaleźć danych zlecenia w podanym linku.")
    top = max(leads, key=lambda x: x.lead_score)
    return {
        "title": top.title,
        "budget_pln": top.budget_pln,
        "vat_required": top.vat_required,
        "contact_phone": top.contact_phone,
        "contact_email": top.contact_email,
        "description": top.description,
        "location": top.location,
        "work_mode": top.work_mode,
        "lead_score": top.lead_score,
        "direct_link": top.direct_link,
    }


def _scan_source(source: CurlCffiB2BSource) -> list[B2BLeadCandidate]:
    source_key = f"b2b:{source.source_name}"
    if source_circuit_breaker.is_open(source_key):
        wait = source_circuit_breaker.remaining_open_seconds(source_key)
        record_source_failure(source_key, f"circuit_open:{wait}s")
        return []

    last_error = ""
    for endpoint in source.endpoints:
        try:
            leads = source.fetch_from_url(endpoint)
            source_circuit_breaker.record_success(source_key)
            record_source_success(source_key, len(leads))
            return leads
        except Exception as exc:
            last_error = str(exc)
            record_source_failure(source_key, f"endpoint_failed:{endpoint}:{exc}")

    tripped = source_circuit_breaker.record_failure(source_key)
    if tripped:
        record_source_failure(source_key, f"circuit_open:{last_error}")
    return []


def _trigger_automations(db: Session, event: str) -> None:
    """Fire all enabled automations matching the given trigger event."""
    try:
        automations = (
            db.query(Automation)
            .filter(Automation.enabled.is_(True), Automation.trigger == event)
            .all()
        )
        for auto in automations:
            logger.info("Automation triggered: %s (action=%s)", auto.name, auto.action)
    except Exception as exc:
        logger.warning("Could not trigger automations for event %s: %s", event, exc)
