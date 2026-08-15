"""Campaigns router."""
from typing import Optional, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Campaign, Lead

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignIn(BaseModel):
    name: str
    description: str = ""
    source: str = ""
    budget: float = 0.0
    target_leads: int = 0
    project_id: str = "default"


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    target_leads: Optional[int] = None


def _bulk_lead_counts(campaign_ids: list, db: Session) -> Dict[int, Tuple[int, int]]:
    """Return {campaign_id: (total, won)} using two aggregate queries (not N+1)."""
    if not campaign_ids:
        return {}
    total_rows = (
        db.query(Lead.campaign_id, func.count(Lead.id))
        .filter(Lead.campaign_id.in_(campaign_ids))
        .group_by(Lead.campaign_id)
        .all()
    )
    won_rows = (
        db.query(Lead.campaign_id, func.count(Lead.id))
        .filter(Lead.campaign_id.in_(campaign_ids), Lead.stage == "wygrany")
        .group_by(Lead.campaign_id)
        .all()
    )
    totals = {cid: cnt for cid, cnt in total_rows}
    wons = {cid: cnt for cid, cnt in won_rows}
    return {cid: (totals.get(cid, 0), wons.get(cid, 0)) for cid in campaign_ids}


@router.get("")
def list_campaigns(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Campaign)
    if project_id:
        q = q.filter(Campaign.project_id == project_id)
    camps = q.order_by(Campaign.created_at.desc()).all()
    counts = _bulk_lead_counts([c.id for c in camps], db)
    return [_ser(c, *counts.get(c.id, (0, 0))) for c in camps]


@router.post("", status_code=201)
def create_campaign(payload: CampaignIn, db: Session = Depends(get_db)):
    c = Campaign(**payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _ser(c, 0, 0)


@router.get("/{campaign_id}")
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Kampania nie znaleziona")
    counts = _bulk_lead_counts([c.id], db)
    total, won = counts.get(c.id, (0, 0))
    return _ser(c, total, won)


@router.patch("/{campaign_id}")
def update_campaign(campaign_id: int, payload: CampaignUpdate, db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Kampania nie znaleziona")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    counts = _bulk_lead_counts([c.id], db)
    total, won = counts.get(c.id, (0, 0))
    return _ser(c, total, won)


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Kampania nie znaleziona")
    db.delete(c)
    db.commit()


def _ser(c: Campaign, total: int, won: int) -> dict:
    conv = round(won / total * 100, 1) if total else 0.0
    return {
        "id": c.id,
        "project_id": c.project_id,
        "name": c.name,
        "description": c.description,
        "status": c.status,
        "source": c.source,
        "budget": c.budget,
        "target_leads": c.target_leads,
        "current_leads": total,
        "won_leads": won,
        "conversion_rate": conv,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
