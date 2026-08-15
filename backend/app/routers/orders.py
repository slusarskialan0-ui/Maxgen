from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from database import get_db
from app.models.models import Order, Client, OrderHistory

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderIn(BaseModel):
    client_id: int
    title: str
    description: str = ""
    value: float = 0.0
    status: str = "nowe"
    project_id: str = "default"


class OrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    value: Optional[float] = None
    status: Optional[str] = None


class OrderHistoryIn(BaseModel):
    note: str = ""
    status_change: str = ""


@router.get("")
def list_orders(
    voivodeship: Optional[str] = None,
    industry: Optional[str] = None,
    status: Optional[str] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(Order).join(Client)
    if voivodeship:
        q = q.filter(Client.voivodeship == voivodeship)
    if industry:
        q = q.filter(Client.industry == industry)
    if status:
        q = q.filter(Order.status == status)
    if min_value is not None:
        q = q.filter(Order.value >= min_value)
    if max_value is not None:
        q = q.filter(Order.value <= max_value)
    total = q.count()
    orders = q.offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": o.id,
                "client_id": o.client_id,
                "client_name": o.client.company_name if o.client else "",
                "title": o.title,
                "description": o.description,
                "value": o.value,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "voivodeship": o.client.voivodeship if o.client else "",
                "industry": o.client.industry if o.client else "",
            }
            for o in orders
        ],
    }


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Zlecenie nie znalezione")
    return {
        "id": o.id,
        "client_id": o.client_id,
        "client_name": o.client.company_name if o.client else "",
        "title": o.title,
        "description": o.description,
        "value": o.value,
        "status": o.status,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "history": [
            {"id": h.id, "note": h.note, "status_change": h.status_change, "created_at": h.created_at.isoformat()}
            for h in o.history
        ],
    }


@router.patch("/{order_id}/status")
def update_order_status(order_id: int, status: str, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Zlecenie nie znalezione")
    old_status = o.status
    o.status = status
    h = OrderHistory(order_id=order_id, note="Zmiana statusu", status_change=f"{old_status} → {status}")
    db.add(h)
    db.commit()
    return {"ok": True}


@router.post("/{order_id}/history")
def add_history(order_id: int, payload: OrderHistoryIn, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Zlecenie nie znalezione")
    h = OrderHistory(order_id=order_id, note=payload.note, status_change=payload.status_change)
    db.add(h)
    db.commit()
    return {"ok": True}


def _ser_order(o: Order) -> dict:
    return {
        "id": o.id,
        "project_id": o.project_id,
        "client_id": o.client_id,
        "client_name": o.client.company_name if o.client else "",
        "title": o.title,
        "description": o.description,
        "value": o.value,
        "status": o.status,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


@router.post("", status_code=201)
def create_order(payload: OrderIn, db: Session = Depends(get_db)):
    if not db.query(Client).filter(Client.id == payload.client_id).first():
        raise HTTPException(status_code=404, detail="Klient nie znaleziony")
    o = Order(**payload.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return _ser_order(o)


@router.patch("/{order_id}")
def update_order(order_id: int, payload: OrderUpdate, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Zlecenie nie znalezione")
    old_status = o.status
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(o, k, v)
    if payload.status and payload.status != old_status:
        db.add(OrderHistory(order_id=order_id, note="Zmiana statusu", status_change=f"{old_status} → {payload.status}"))
    db.commit()
    db.refresh(o)
    return _ser_order(o)


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Zlecenie nie znalezione")
    db.query(OrderHistory).filter(OrderHistory.order_id == order_id).delete()
    db.delete(o)
    db.commit()
