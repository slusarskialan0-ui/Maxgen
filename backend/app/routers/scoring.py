"""Scoring router — scoring records and lead score management."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Lead, ScoreRecord, Log

router = APIRouter(prefix="/scoring", tags=["scoring"])


class ScoreIn(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    lead_id: int
    score: float
    conversion_probability: Optional[float] = None
    reason: str = ""
    model_version: str = "heuristic-v1"


class ScoreUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    score: Optional[float] = None
    conversion_probability: Optional[float] = None
    reason: Optional[str] = None
    model_version: Optional[str] = None


@router.get("")
def list_scores(
    lead_id: Optional[int] = None,
    min_score: Optional[float] = None,
    model_version: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    q = db.query(ScoreRecord)
    if lead_id is not None:
        q = q.filter(ScoreRecord.lead_id == lead_id)
    if min_score is not None:
        q = q.filter(ScoreRecord.score >= min_score)
    if model_version:
        q = q.filter(ScoreRecord.model_version == model_version)
    rows = q.order_by(ScoreRecord.updated_at.desc(), ScoreRecord.id.desc()).limit(max(1, min(limit, 500))).all()
    return [_ser(row) for row in rows]


@router.post("", status_code=201)
def create_score(payload: ScoreIn, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nie znaleziony")
    prob = payload.conversion_probability
    if prob is None:
        prob = round(min(max(payload.score / 100.0, 0.0), 1.0), 3)
    row = ScoreRecord(
        lead_id=payload.lead_id,
        score=max(0.0, min(payload.score, 100.0)),
        conversion_probability=max(0.0, min(prob, 1.0)),
        reason=payload.reason,
        model_version=payload.model_version,
    )
    lead.score = row.score
    lead.conversion_probability = row.conversion_probability
    lead.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.add(Log(category="scoring", message=f"Scored lead #{lead.id}", metadata_text=f"score={row.score};model={row.model_version}"))
    db.commit()
    db.refresh(row)
    return _ser(row)


@router.get("/{score_id}")
def get_score(score_id: int, db: Session = Depends(get_db)):
    row = db.query(ScoreRecord).filter(ScoreRecord.id == score_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Scoring record nie znaleziony")
    return _ser(row)


@router.patch("/{score_id}")
def update_score(score_id: int, payload: ScoreUpdate, db: Session = Depends(get_db)):
    row = db.query(ScoreRecord).filter(ScoreRecord.id == score_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Scoring record nie znaleziony")
    updates = payload.model_dump(exclude_none=True)
    for key, value in updates.items():
        if key == "score":
            value = max(0.0, min(value, 100.0))
        if key == "conversion_probability":
            value = max(0.0, min(value, 1.0))
        setattr(row, key, value)
    if "score" in updates or "conversion_probability" in updates:
        lead = db.query(Lead).filter(Lead.id == row.lead_id).first()
        if lead:
            lead.score = row.score
            lead.conversion_probability = row.conversion_probability
            lead.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.add(Log(category="scoring", message=f"Updated score record #{row.id}", metadata_text=f"lead_id={row.lead_id}"))
    db.commit()
    db.refresh(row)
    return _ser(row)


@router.delete("/{score_id}", status_code=204)
def delete_score(score_id: int, db: Session = Depends(get_db)):
    row = db.query(ScoreRecord).filter(ScoreRecord.id == score_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Scoring record nie znaleziony")
    db.add(Log(category="scoring", message=f"Deleted score record #{row.id}", metadata_text=f"lead_id={row.lead_id}"))
    db.delete(row)
    db.commit()


def _ser(row: ScoreRecord):
    return {
        "id": row.id,
        "lead_id": row.lead_id,
        "score": row.score,
        "conversion_probability": row.conversion_probability,
        "reason": row.reason,
        "model_version": row.model_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
