"""Offers router."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Lead, Offer

router = APIRouter(prefix="/offers", tags=["offers"])


class OfferIn(BaseModel):
    title: str
    description: str = ""
    amount: float = 0.0
    currency: str = "PLN"
    status: str = "draft"
    lead_id: Optional[int] = None
    project_id: str = "default"


class OfferUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None


@router.get("")
def list_offers(status: Optional[str] = None, lead_id: Optional[int] = None, project_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Offer)
    if status:
        q = q.filter(Offer.status == status)
    if lead_id is not None:
        q = q.filter(Offer.lead_id == lead_id)
    if project_id:
        q = q.filter(Offer.project_id == project_id)
    return [_ser(o) for o in q.order_by(Offer.created_at.desc()).limit(200).all()]


@router.post("", status_code=201)
def create_offer(payload: OfferIn, db: Session = Depends(get_db)):
    if payload.lead_id:
        lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    o = Offer(**payload.model_dump())
    if o.status == "sent":
        o.sent_at = datetime.now(timezone.utc)
    if o.status == "accepted":
        o.accepted_at = datetime.now(timezone.utc)
    db.add(o)
    db.commit()
    db.refresh(o)
    return _ser(o)


@router.patch("/{offer_id}")
def update_offer(offer_id: int, payload: OfferUpdate, db: Session = Depends(get_db)):
    o = db.query(Offer).filter(Offer.id == offer_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Oferta nie znaleziona")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(o, k, v)
    if payload.status == "sent":
        o.sent_at = datetime.now(timezone.utc)
    if payload.status == "accepted":
        o.accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(o)
    return _ser(o)


@router.delete("/{offer_id}", status_code=204)
def delete_offer(offer_id: int, db: Session = Depends(get_db)):
    o = db.query(Offer).filter(Offer.id == offer_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Oferta nie znaleziona")
    db.delete(o)
    db.commit()


def _ser(o: Offer):
    return {
        "id": o.id,
        "project_id": o.project_id,
        "lead_id": o.lead_id,
        "title": o.title,
        "description": o.description,
        "amount": o.amount,
        "currency": o.currency,
        "status": o.status,
        "sent_at": o.sent_at.isoformat() if o.sent_at else None,
        "accepted_at": o.accepted_at.isoformat() if o.accepted_at else None,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }
