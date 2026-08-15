"""Automation facade used by routers and background tasks."""
from sqlalchemy.orm import Session

from app.models.models import Lead
from app.services.offline_engine_service import run_sales_automations


def run_for_all_open_leads(db: Session) -> dict:
    leads = db.query(Lead).filter(Lead.stage.not_in(["wygrany", "przegrany"])).all()
    return run_sales_automations(db, leads)


def run_for_lead(db: Session, lead_id: int) -> dict:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return {"assigned": 0, "follow_ups": 0, "closed": 0, "offers_generated": 0}
    return run_sales_automations(db, [lead])
