"""Offers router."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Offer, Lead, LogEntry

router = APIRouter(prefix="/offers", tags=["offers"])


class OfferIn(BaseModel):
    lead_id: int
    campaign_id: Optional[int] = None
    title: str
    description: str = ""
    amount: float = 0.0
    currency: str = "PLN"
    status: str = "draft"
    valid_days: int = 14


class OfferUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    valid_until: Optional[datetime] = None


@router.get("")
def list_offers(status: Optional[str] = None, lead_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Offer)
    if status:
        q = q.filter(Offer.status == status)
    if lead_id:
        q = q.filter(Offer.lead_id == lead_id)
    return [_ser(o) for o in q.order_by(Offer.created_at.desc()).limit(200).all()]


@router.post("", status_code=201)
def create_offer(payload: OfferIn, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    offer = Offer(
        lead_id=payload.lead_id,
        campaign_id=payload.campaign_id,
        title=payload.title,
        description=payload.description,
        amount=payload.amount,
        currency=payload.currency,
        status=payload.status,
        valid_until=datetime.utcnow() + timedelta(days=max(payload.valid_days, 1)),
    )
    db.add(offer)
    db.add(LogEntry(module="offers", level="INFO", event="offer_created", details=f"offer:{offer.title} lead:{payload.lead_id}"))
    db.commit()
    db.refresh(offer)
    return _ser(offer)


@router.get("/{offer_id}")
def get_offer(offer_id: int, db: Session = Depends(get_db)):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta nie znaleziona")
    return _ser(offer)


@router.patch("/{offer_id}")
def update_offer(offer_id: int, payload: OfferUpdate, db: Session = Depends(get_db)):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta nie znaleziona")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(offer, key, value)
    db.add(LogEntry(module="offers", level="INFO", event="offer_updated", details=f"offer_id:{offer.id} status:{offer.status}"))
    db.commit()
    db.refresh(offer)
    return _ser(offer)


@router.delete("/{offer_id}", status_code=204)
def delete_offer(offer_id: int, db: Session = Depends(get_db)):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta nie znaleziona")
    db.add(LogEntry(module="offers", level="WARN", event="offer_deleted", details=f"offer_id:{offer.id}"))
    db.delete(offer)
    db.commit()


def _ser(offer: Offer) -> dict:
    return {
        "id": offer.id,
        "lead_id": offer.lead_id,
        "campaign_id": offer.campaign_id,
        "title": offer.title,
        "description": offer.description,
        "amount": offer.amount,
        "currency": offer.currency,
        "status": offer.status,
        "valid_until": offer.valid_until.isoformat() if offer.valid_until else None,
        "created_at": offer.created_at.isoformat() if offer.created_at else None,
        "updated_at": offer.updated_at.isoformat() if offer.updated_at else None,
    }
