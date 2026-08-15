"""Payments router — offline transaction simulation."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Lead, Payment
from app.services.offline_engine_service import simulate_payment

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIn(BaseModel):
    lead_id: int
    amount: float
    offer_id: Optional[int] = None


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    log: Optional[str] = None


@router.get("")
def list_payments(lead_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Payment)
    if lead_id is not None:
        q = q.filter(Payment.lead_id == lead_id)
    rows = q.order_by(Payment.created_at.desc()).limit(200).all()
    return [_ser(p) for p in rows]


@router.post("/simulate", status_code=201)
def create_payment_simulation(payload: PaymentIn, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    payment = simulate_payment(db, payload.lead_id, payload.amount, payload.offer_id)
    db.commit()
    db.refresh(payment)
    return _ser(payment)


@router.patch("/{payment_id}")
def update_payment(payment_id: int, payload: PaymentUpdate, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Płatność nie znaleziona")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(payment, k, v)
    db.commit()
    db.refresh(payment)
    return _ser(payment)


def _ser(p: Payment) -> dict:
    return {
        "id": p.id,
        "lead_id": p.lead_id,
        "offer_id": p.offer_id,
        "amount": p.amount,
        "status": p.status,
        "method": p.method,
        "confirmation_code": p.confirmation_code,
        "log": p.log,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
