"""Payments router."""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Lead, Payment, PaymentLog

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIn(BaseModel):
    lead_id: Optional[int] = None
    amount: float
    currency: str = "PLN"
    method: str = "przelew"
    description: str = ""


def _log_payment(db: Session, payment_id: Optional[int], event: str, details: str):
    db.add(PaymentLog(payment_id=payment_id, event=event, details=details))


def _serialize(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "lead_id": payment.lead_id,
        "amount": payment.amount,
        "currency": payment.currency,
        "method": payment.method,
        "description": payment.description,
        "status": payment.status,
        "transaction_id": payment.transaction_id,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "confirmed_at": payment.confirmed_at.isoformat() if payment.confirmed_at else None,
    }


@router.get("")
def list_payments(db: Session = Depends(get_db)):
    return [_serialize(p) for p in db.query(Payment).order_by(Payment.created_at.desc()).all()]


@router.post("", status_code=201)
def create_payment(payload: PaymentIn, db: Session = Depends(get_db)):
    if payload.lead_id is not None and not db.query(Lead).filter(Lead.id == payload.lead_id).first():
        raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    payment = Payment(
        lead_id=payload.lead_id,
        amount=payload.amount,
        currency=payload.currency,
        method=payload.method,
        description=payload.description,
        transaction_id=str(uuid.uuid4()),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    _log_payment(db, payment.id, "PAYMENT_CREATED", f"Utworzono płatność {payment.transaction_id} na kwotę {payment.amount} {payment.currency}.")
    db.commit()
    return _serialize(payment)


@router.get("/stats")
def payment_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Payment.id)).scalar() or 0
    confirmed = db.query(func.count(Payment.id)).filter(Payment.status == "potwierdzona").scalar() or 0
    rejected = db.query(func.count(Payment.id)).filter(Payment.status == "odrzucona").scalar() or 0
    total_amount = db.query(func.coalesce(func.sum(Payment.amount), 0.0)).scalar() or 0.0
    return {
        "total": total,
        "confirmed": confirmed,
        "rejected": rejected,
        "total_amount": round(float(total_amount), 2),
    }


@router.get("/logs")
def payment_logs(db: Session = Depends(get_db)):
    logs = db.query(PaymentLog).order_by(PaymentLog.created_at.desc()).limit(50).all()
    return [
        {
            "id": log.id,
            "payment_id": log.payment_id,
            "event": log.event,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/{payment_id}")
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Płatność nie znaleziona")
    return _serialize(payment)


@router.patch("/{payment_id}/confirm")
def confirm_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Płatność nie znaleziona")
    payment.status = "potwierdzona"
    payment.confirmed_at = datetime.utcnow()
    _log_payment(db, payment.id, "PAYMENT_CONFIRMED", f"Płatność {payment.transaction_id} została potwierdzona.")
    db.commit()
    db.refresh(payment)
    return _serialize(payment)


@router.patch("/{payment_id}/reject")
def reject_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Płatność nie znaleziona")
    payment.status = "odrzucona"
    payment.confirmed_at = None
    _log_payment(db, payment.id, "PAYMENT_REJECTED", f"Płatność {payment.transaction_id} została odrzucona.")
    db.commit()
    db.refresh(payment)
    return _serialize(payment)
