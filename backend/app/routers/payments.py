"""Payments router (offline simulation)."""
import random
import string
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Payment, Offer, Lead, LogEntry

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIn(BaseModel):
    lead_id: Optional[int] = None
    offer_id: Optional[int] = None
    amount: float = 0.0
    currency: str = "PLN"
    method: str = "offline_transfer"
    note: str = ""


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None


def _confirmation() -> str:
    return "OFF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


@router.get("")
def list_payments(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Payment)
    if status:
        q = q.filter(Payment.status == status)
    return [_ser(p) for p in q.order_by(Payment.created_at.desc()).limit(200).all()]


@router.post("", status_code=201)
def create_payment(payload: PaymentIn, db: Session = Depends(get_db)):
    if payload.offer_id:
        offer = db.query(Offer).filter(Offer.id == payload.offer_id).first()
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta nie znaleziona")
    if payload.lead_id:
        lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    payment = Payment(
        lead_id=payload.lead_id,
        offer_id=payload.offer_id,
        amount=payload.amount,
        currency=payload.currency,
        method=payload.method,
        status="pending",
        confirmation_code="",
        note=payload.note,
    )
    db.add(payment)
    db.add(LogEntry(module="payments", level="INFO", event="payment_created", details=f"amount:{payload.amount} status:pending"))
    db.commit()
    db.refresh(payment)
    return _ser(payment)


@router.patch("/{payment_id}")
def update_payment(payment_id: int, payload: PaymentUpdate, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Płatność nie znaleziona")
    if payload.status:
        payment.status = payload.status
        if payload.status == "confirmed" and not payment.confirmation_code:
            payment.confirmation_code = _confirmation()
    if payload.note is not None:
        payment.note = payload.note
    db.add(LogEntry(module="payments", level="INFO", event="payment_updated", details=f"payment_id:{payment.id} status:{payment.status}"))
    db.commit()
    db.refresh(payment)
    return _ser(payment)


@router.post("/{payment_id}/confirm")
def confirm_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Płatność nie znaleziona")
    payment.status = "confirmed"
    payment.confirmation_code = payment.confirmation_code or _confirmation()
    db.add(LogEntry(module="payments", level="INFO", event="payment_confirmed", details=f"payment_id:{payment.id} code:{payment.confirmation_code}"))
    db.commit()
    db.refresh(payment)
    return _ser(payment)


@router.get("/logs/recent")
def payment_logs(db: Session = Depends(get_db)):
    rows = (
        db.query(LogEntry)
        .filter(LogEntry.module == "payments")
        .order_by(LogEntry.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": row.id,
            "module": row.module,
            "level": row.level,
            "event": row.event,
            "details": row.details,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def _ser(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "lead_id": payment.lead_id,
        "offer_id": payment.offer_id,
        "amount": payment.amount,
        "currency": payment.currency,
        "method": payment.method,
        "status": payment.status,
        "confirmation_code": payment.confirmation_code,
        "note": payment.note,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "updated_at": payment.updated_at.isoformat() if payment.updated_at else None,
    }
