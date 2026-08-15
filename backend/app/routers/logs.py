"""Logs router — CRUD for operational logs (admin maintenance use case)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Log

router = APIRouter(prefix="/logs", tags=["logs"])


class LogIn(BaseModel):
    category: str
    message: str = ""
    metadata_text: str = ""


class LogUpdate(BaseModel):
    category: Optional[str] = None
    message: Optional[str] = None
    metadata_text: Optional[str] = None


@router.get("")
def list_logs(
    category: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(Log)
    if category:
        query = query.filter(Log.category == category)
    if q:
        query = query.filter(Log.message.ilike(f"%{q}%"))
    rows = query.order_by(Log.created_at.desc(), Log.id.desc()).limit(max(1, min(limit, 500))).all()
    return [_ser(row) for row in rows]


@router.post("", status_code=201)
def create_log(payload: LogIn, db: Session = Depends(get_db)):
    row = Log(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _ser(row)


@router.get("/{log_id}")
def get_log(log_id: int, db: Session = Depends(get_db)):
    row = db.query(Log).filter(Log.id == log_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Log nie znaleziony")
    return _ser(row)


@router.patch("/{log_id}")
def update_log(log_id: int, payload: LogUpdate, db: Session = Depends(get_db)):
    row = db.query(Log).filter(Log.id == log_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Log nie znaleziony")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _ser(row)


@router.delete("/{log_id}", status_code=204)
def delete_log(log_id: int, db: Session = Depends(get_db)):
    row = db.query(Log).filter(Log.id == log_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Log nie znaleziony")
    db.delete(row)
    db.commit()


def _ser(row: Log):
    return {
        "id": row.id,
        "category": row.category,
        "message": row.message,
        "metadata_text": row.metadata_text,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
