"""Payments router with offline simulation."""
import random
import string
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Lead, Offer, Payment, PaymentLog

router = APIRouter(prefix="/payments", tags=["payments"])


def _confirmation_code() -> str:
    return "OFF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


class PaymentIn(BaseModel):
    amount: float
    currency: str = "PLN"
    method: str = "offline_transfer"
    status: str = "pending"
    note: str = ""
    lead_id: Optional[int] = None
    offer_id: Optional[int] = None
    project_id: str = "default"


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None


@router.get("")
def list_payments(status: Optional[str] = None, lead_id: Optional[int] = None, offer_id: Optional[int] = None, project_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Payment)
    if status:
        q = q.filter(Payment.status == status)
    if lead_id is not None:
        q = q.filter(Payment.lead_id == lead_id)
    if offer_id is not None:
        q = q.filter(Payment.offer_id == offer_id)
    if project_id:
        q = q.filter(Payment.project_id == project_id)
    return [_ser(p) for p in q.order_by(Payment.created_at.desc()).limit(200).all()]


@router.post("", status_code=201)
def create_payment(payload: PaymentIn, db: Session = Depends(get_db)):
    if payload.lead_id and not db.query(Lead).filter(Lead.id == payload.lead_id).first():
        raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    if payload.offer_id and not db.query(Offer).filter(Offer.id == payload.offer_id).first():
        raise HTTPException(status_code=404, detail="Oferta nie znaleziona")
    p = Payment(**payload.model_dump())
    if p.status == "confirmed":
        p.confirmed_at = datetime.utcnow()
        p.confirmation_code = _confirmation_code()
    db.add(p)
    db.commit()
    db.refresh(p)
    db.add(PaymentLog(payment_id=p.id, action="created", details=f"status={p.status}"))
    db.commit()
    return _ser(p)


@router.patch("/{payment_id}")
def update_payment(payment_id: int, payload: PaymentUpdate, db: Session = Depends(get_db)):
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Płatność nie znaleziona")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    if payload.status == "confirmed":
        p.confirmed_at = datetime.utcnow()
        if not p.confirmation_code:
            p.confirmation_code = _confirmation_code()
    db.commit()
    db.refresh(p)
    if payload.status:
        db.add(PaymentLog(payment_id=p.id, action=payload.status, details=payload.note or ""))
        db.commit()
    return _ser(p)


@router.get("/{payment_id}/logs")
def payment_logs(payment_id: int, db: Session = Depends(get_db)):
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Płatność nie znaleziona")
    logs = db.query(PaymentLog).filter(PaymentLog.payment_id == payment_id).order_by(PaymentLog.created_at.desc()).all()
    return [
        {"id": log.id, "payment_id": log.payment_id, "action": log.action, "details": log.details, "created_at": log.created_at.isoformat() if log.created_at else None}
        for log in logs
    ]


@router.post("/{payment_id}/simulate")
def simulate_payment(payment_id: int, force_status: Optional[str] = None, db: Session = Depends(get_db)):
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Płatność nie znaleziona")
    allowed = {"pending", "confirmed", "failed", "refunded"}
    if force_status and force_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Nieobsługiwany status: {force_status}")
    p.status = force_status or random.choice(["confirmed", "failed", "pending"])
    if p.status == "confirmed":
        p.confirmed_at = datetime.utcnow()
        if not p.confirmation_code:
            p.confirmation_code = _confirmation_code()
    db.commit()
    db.refresh(p)
    db.add(PaymentLog(payment_id=p.id, action="simulate", details=f"new_status={p.status}"))
    db.commit()
    return _ser(p)


def _ser(p: Payment):
    return {
        "id": p.id,
        "project_id": p.project_id,
        "lead_id": p.lead_id,
        "offer_id": p.offer_id,
        "amount": p.amount,
        "currency": p.currency,
        "method": p.method,
        "status": p.status,
        "confirmation_code": p.confirmation_code,
        "note": p.note,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "confirmed_at": p.confirmed_at.isoformat() if p.confirmed_at else None,
    }
