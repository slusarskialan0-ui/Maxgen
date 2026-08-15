"""Users router."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import UserProfile

router = APIRouter(prefix="/users", tags=["users"])


class UserIn(BaseModel):
    username: str
    display_name: str = ""
    role: str = "agent"
    email: str = ""


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = None


@router.get("")
def list_users(db: Session = Depends(get_db)):
    return [_ser(u) for u in db.query(UserProfile).order_by(UserProfile.id).all()]


@router.post("", status_code=201)
def create_user(payload: UserIn, db: Session = Depends(get_db)):
    if db.query(UserProfile).filter(UserProfile.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Użytkownik już istnieje")
    u = UserProfile(**payload.model_dump())
    db.add(u)
    db.commit()
    db.refresh(u)
    return _ser(u)


@router.patch("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    u = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(u, k, v)
    db.commit()
    db.refresh(u)
    return _ser(u)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    db.delete(u)
    db.commit()


def _ser(u: UserProfile) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "display_name": u.display_name,
        "role": u.role,
        "email": u.email,
        "active": u.active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }
