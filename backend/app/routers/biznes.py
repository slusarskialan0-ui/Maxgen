from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from app.models.models import Client, Order
from app.routers.devplatform import api_request_log

router = APIRouter(prefix="/biznes", tags=["biznes"])

PLAN_DEFINITIONS = [
    {
        "name": "Free",
        "price": 0,
        "leads": 150,
        "api_requests_month": 5000,
        "features": ["1 pipeline", "Podstawowy CRM", "Eksport CSV/JSON"],
    },
    {
        "name": "Starter",
        "price": 299,
        "leads": 500,
        "api_requests_month": 25000,
        "features": ["1 pipeline", "Podstawowy CRM", "Eksport CSV/JSON"],
    },
    {
        "name": "Pro",
        "price": 799,
        "leads": 2000,
        "api_requests_month": 120000,
        "features": ["Multi-województwa", "API access", "Automatyzacje follow-up"],
    },
    {
        "name": "Agency",
        "price": 1499,
        "leads": 7000,
        "api_requests_month": 300000,
        "features": ["Multi-project", "White-label", "Panel agencyjny", "Marketplace leadów"],
    },
    {
        "name": "Enterprise",
        "price": 1999,
        "leads": "unlimited",
        "api_requests_month": "unlimited",
        "features": ["Unlimited leads", "White-label", "Dedykowany opiekun"],
    },
]


def _today_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _month_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


@router.get("/pricing")
def pricing(db: Session = Depends(get_db)):
    total_clients = db.query(Client).count()
    demand_factor = round(1.0 + min(total_clients / 10000, 0.35), 2)
    recommended = "Free" if total_clients < 100 else "Starter" if total_clients < 500 else "Pro" if total_clients < 2000 else "Agency"
    return {
        "tiers": PLAN_DEFINITIONS,
        "recommended": recommended,
        "demand_factor": demand_factor,
    }


@router.get("/billing")
def billing():
    today = datetime.now(timezone.utc).date()
    return {
        "invoices": [
            {"id": f"INV-{(today - timedelta(days=35)).strftime('%Y-%m%d')}", "date": str(today - timedelta(days=35)), "amount": 799, "status": "paid"},
            {"id": f"INV-{(today - timedelta(days=65)).strftime('%Y-%m%d')}", "date": str(today - timedelta(days=65)), "amount": 799, "status": "paid"},
            {"id": f"INV-{(today - timedelta(days=95)).strftime('%Y-%m%d')}", "date": str(today - timedelta(days=95)), "amount": 599, "status": "paid"},
        ],
        "next_invoice": str(today + timedelta(days=14)),
        "subscription": "Pro",
    }


@router.get("/marketplace")
def marketplace(db: Session = Depends(get_db)):
    rows = (
        db.query(
            Client.id,
            Client.company_name,
            Client.industry,
            Client.voivodeship,
            Client.city,
            Client.email,
            Client.phone,
            func.coalesce(func.sum(Order.value), 0.0).label("order_value"),
            func.count(Order.id).label("orders_count"),
        )
        .outerjoin(Order, Order.client_id == Client.id)
        .group_by(Client.id)
        .order_by(func.coalesce(func.sum(Order.value), 0.0).desc(), func.count(Order.id).desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": client_id,
            "company_name": company_name,
            "industry": industry,
            "voivodeship": voivodeship,
            "city": city,
            "email": email,
            "phone": phone,
            "order_value": float(order_value or 0.0),
            "orders_count": int(orders_count or 0),
        }
        for client_id, company_name, industry, voivodeship, city, email, phone, order_value, orders_count in rows
    ]


@router.get("/agency-dashboard")
def agency_dashboard(db: Session = Depends(get_db)):
    client_rows = db.query(Client.project_id, func.count(Client.id)).group_by(Client.project_id).all()
    revenue_rows = (
        db.query(Order.project_id, func.coalesce(func.sum(Order.value), 0.0))
        .group_by(Order.project_id)
        .all()
    )
    top_industries = (
        db.query(Client.industry, func.count(Client.id))
        .group_by(Client.industry)
        .order_by(func.count(Client.id).desc())
        .limit(5)
        .all()
    )
    return {
        "total_projects": len({project_id for project_id, _ in client_rows} | {project_id for project_id, _ in revenue_rows}) or 1,
        "clients_per_project": {project_id or "default": int(count or 0) for project_id, count in client_rows} or {"default": 0},
        "revenue_per_project": {project_id or "default": float(value or 0.0) for project_id, value in revenue_rows} or {"default": 0.0},
        "top_industries": [{"industry": industry or "Nieznana", "count": int(count or 0)} for industry, count in top_industries],
    }


@router.get("/subscriptions")
def subscriptions(db: Session = Depends(get_db)):
    leads_used = db.query(Client).count()
    return {
        "plans": [plan["name"] for plan in PLAN_DEFINITIONS],
        "active_plan": "Pro",
        "usage": {"leads_used": leads_used, "leads_limit": 2000},
    }


@router.get("/usage")
def usage(db: Session = Depends(get_db)):
    today = _today_prefix()
    month = _month_prefix()
    return {
        "api_requests_today": sum(1 for entry in api_request_log if entry["ts"].startswith(today)),
        "api_requests_month": sum(1 for entry in api_request_log if entry["ts"].startswith(month)),
        "leads_acquired": db.query(Client).count(),
        "orders_created": db.query(Order).count(),
    }


@router.get("/plan-upgrade-preview")
def plan_upgrade_preview(active_plan: str = "Free", db: Session = Depends(get_db)):
    plans = {plan["name"]: plan for plan in PLAN_DEFINITIONS}
    active = plans.get(active_plan, plans["Free"])
    leads_used = db.query(Client).count()
    api_month = sum(1 for entry in api_request_log if entry["ts"].startswith(_month_prefix()))
    leads_limit = active["leads"] if isinstance(active["leads"], int) else None
    api_limit = active["api_requests_month"] if isinstance(active["api_requests_month"], int) else None
    leads_pct = round((leads_used / leads_limit) * 100, 2) if leads_limit else None
    api_pct = round((api_month / api_limit) * 100, 2) if api_limit else None

    next_plan = None
    if active["name"] != "Enterprise":
        idx = [p["name"] for p in PLAN_DEFINITIONS].index(active["name"])
        next_plan = PLAN_DEFINITIONS[min(idx + 1, len(PLAN_DEFINITIONS) - 1)]["name"]
    upgrade_recommended = bool((leads_pct and leads_pct >= 80) or (api_pct and api_pct >= 80))
    return {
        "active_plan": active["name"],
        "next_plan": next_plan,
        "usage": {
            "leads_used": leads_used,
            "leads_limit": active["leads"],
            "leads_usage_pct": leads_pct,
            "api_requests_month": api_month,
            "api_requests_limit": active["api_requests_month"],
            "api_usage_pct": api_pct,
        },
        "upgrade_recommended": upgrade_recommended,
    }


@router.get("/segments")
def segments(db: Session = Depends(get_db)):
    industry = (
        db.query(Client.industry, func.count(Client.id))
        .group_by(Client.industry)
        .order_by(func.count(Client.id).desc())
        .limit(8)
        .all()
    )
    voivodeships = (
        db.query(Client.voivodeship, func.count(Client.id))
        .group_by(Client.voivodeship)
        .order_by(func.count(Client.id).desc())
        .limit(8)
        .all()
    )
    projects = (
        db.query(
            Client.project_id,
            func.count(func.distinct(Client.id)),
            func.coalesce(func.sum(Order.value), 0.0),
        )
        .outerjoin(Order, Order.client_id == Client.id)
        .group_by(Client.project_id)
        .order_by(func.count(func.distinct(Client.id)).desc())
        .limit(10)
        .all()
    )
    return {
        "by_industry": [{"industry": key or "Nieznana", "count": int(value or 0)} for key, value in industry],
        "by_voivodeship": [{"voivodeship": key or "Nieznane", "count": int(value or 0)} for key, value in voivodeships],
        "by_project": [
            {"project_id": pid or "default", "clients": int(clients or 0), "revenue": float(revenue or 0.0)}
            for pid, clients, revenue in projects
        ],
    }
