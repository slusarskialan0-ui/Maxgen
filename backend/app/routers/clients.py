from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from database import get_db
from app.models.models import Client, Order

router = APIRouter(prefix="/clients", tags=["clients"])


class ClientIn(BaseModel):
    company_name: str
    industry: str = ""
    voivodeship: str = ""
    county: str = ""
    city: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    source_type: str = ""
    source_detail: str = ""
    status: str = "nowy"
    project_id: str = "default"


class ClientUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    voivodeship: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    source_type: Optional[str] = None
    source_detail: Optional[str] = None
    status: Optional[str] = None


@router.get("")
def list_clients(
    voivodeship: Optional[str] = None,
    industry: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(Client)
    if voivodeship:
        q = q.filter(Client.voivodeship == voivodeship)
    if industry:
        q = q.filter(Client.industry == industry)
    if source_type:
        q = q.filter(Client.source_type == source_type)
    if status:
        q = q.filter(Client.status == status)
    total = q.count()
    clients = q.offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": c.id,
                "company_name": c.company_name,
                "industry": c.industry,
                "voivodeship": c.voivodeship,
                "county": c.county,
                "city": c.city,
                "email": c.email,
                "phone": c.phone,
                "website": c.website,
                "source_type": c.source_type,
                "source_detail": c.source_detail,
                "acquired_at": c.acquired_at.isoformat() if c.acquired_at else None,
                "status": c.status,
            }
            for c in clients
        ],
    }


@router.get("/{client_id}")
def get_client(client_id: int, db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klient nie znaleziony")
    orders = [
        {
            "id": o.id,
            "title": o.title,
            "description": o.description,
            "value": o.value,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in c.orders
    ]
    return {
        "id": c.id,
        "company_name": c.company_name,
        "industry": c.industry,
        "voivodeship": c.voivodeship,
        "county": c.county,
        "city": c.city,
        "email": c.email,
        "phone": c.phone,
        "website": c.website,
        "source_type": c.source_type,
        "source_detail": c.source_detail,
        "acquired_at": c.acquired_at.isoformat() if c.acquired_at else None,
        "status": c.status,
        "orders": orders,
    }


@router.patch("/{client_id}/status")
def update_client_status(client_id: int, status: str, db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klient nie znaleziony")
    c.status = status
    db.commit()
    return {"ok": True}


def _ser_client(c: Client) -> dict:
    return {
        "id": c.id,
        "project_id": c.project_id,
        "company_name": c.company_name,
        "industry": c.industry,
        "voivodeship": c.voivodeship,
        "county": c.county,
        "city": c.city,
        "email": c.email,
        "phone": c.phone,
        "website": c.website,
        "source_type": c.source_type,
        "source_detail": c.source_detail,
        "acquired_at": c.acquired_at.isoformat() if c.acquired_at else None,
        "status": c.status,
    }


@router.post("", status_code=201)
def create_client(payload: ClientIn, db: Session = Depends(get_db)):
    c = Client(**payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _ser_client(c)


@router.patch("/{client_id}")
def update_client(client_id: int, payload: ClientUpdate, db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klient nie znaleziony")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return _ser_client(c)


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klient nie znaleziony")
    from app.models.models import OrderHistory
    order_ids = [o.id for o in db.query(Order).filter(Order.client_id == client_id).all()]
    if order_ids:
        db.query(OrderHistory).filter(OrderHistory.order_id.in_(order_ids)).delete(synchronize_session=False)
        db.query(Order).filter(Order.client_id == client_id).delete(synchronize_session=False)
    db.delete(c)
    db.commit()
