"""Offers router — offline generation and lifecycle."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Lead, Offer
from app.services.offline_engine_service import generate_offer_for_lead

router = APIRouter(prefix="/offers", tags=["offers"])


class OfferIn(BaseModel):
    lead_id: int
    title: Optional[str] = None
    amount: Optional[float] = None


class OfferUpdate(BaseModel):
    status: Optional[str] = None
    content: Optional[str] = None


@router.get("")
def list_offers(lead_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Offer)
    if lead_id is not None:
        q = q.filter(Offer.lead_id == lead_id)
    rows = q.order_by(Offer.created_at.desc()).limit(200).all()
    return [_ser(o) for o in rows]


@router.post("", status_code=201)
def create_offer(payload: OfferIn, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    offer = generate_offer_for_lead(db, lead, payload.amount)
    if payload.title:
        offer.title = payload.title
    db.commit()
    db.refresh(offer)
    return _ser(offer)


@router.patch("/{offer_id}")
def update_offer(offer_id: int, payload: OfferUpdate, db: Session = Depends(get_db)):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta nie znaleziona")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(offer, k, v)
    db.commit()
    db.refresh(offer)
    return _ser(offer)


def _ser(o: Offer) -> dict:
    return {
        "id": o.id,
        "lead_id": o.lead_id,
        "title": o.title,
        "amount": o.amount,
        "status": o.status,
        "content": o.content,
        "generated_offline": o.generated_offline,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }
