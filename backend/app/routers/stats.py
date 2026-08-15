from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from app.models.models import Client, Order, AcquisitionLog, Lead, Offer, Payment

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    total_clients = db.query(Client).count()
    total_orders = db.query(Order).count()

    by_voivodeship = (
        db.query(Client.voivodeship, func.count(Client.id))
        .group_by(Client.voivodeship)
        .all()
    )
    by_industry = (
        db.query(Client.industry, func.count(Client.id))
        .group_by(Client.industry)
        .all()
    )
    by_source = (
        db.query(Client.source_type, func.count(Client.id))
        .group_by(Client.source_type)
        .all()
    )

    total_leads = db.query(Lead).count()
    won_leads = db.query(Lead).filter(Lead.stage == "wygrany").count()
    total_offers = db.query(Offer).count()
    total_payments = db.query(Payment).count()
    revenue_total = float(db.query(func.coalesce(func.sum(Payment.amount), 0.0)).scalar() or 0.0)

    return {
        "total_clients": total_clients,
        "total_orders": total_orders,
        "total_leads": total_leads,
        "won_leads": won_leads,
        "conversion_rate_pct": round((won_leads / total_leads) * 100, 2) if total_leads else 0.0,
        "total_offers": total_offers,
        "total_payments": total_payments,
        "revenue_total": revenue_total,
        "by_voivodeship": [{"voivodeship": v, "count": c} for v, c in by_voivodeship],
        "by_industry": [{"industry": i, "count": c} for i, c in by_industry],
        "by_source": [{"source_type": s, "count": c} for s, c in by_source],
    }
