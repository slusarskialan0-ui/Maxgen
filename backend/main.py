"""Main FastAPI application entry point."""
import asyncio
import sys
import os
import time
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import engine, Base, SessionLocal
from sqlalchemy.orm import Session
from app.models.models import Industry, VoivodeshipStatus
from app.data.geography import DEFAULT_INDUSTRIES, VOIVODESHIPS
from app.routers import (
    analytics,
    auto_ops,
    automations,
    biznes,
    campaigns,
    clients,
    devplatform,
    industries,
    leads,
    offers,
    orders,
    payments,
    pipeline,
    security,
    stats,
    sync,
    system,
    users,
    voivodeships,
)
from config import API_HOST, API_PORT, CORS_ORIGINS, APP_VERSION

# Simple in-process cache store (key -> (value, expires_at))
_cache: dict = {}


def cache_get(key: str):
    entry = _cache.get(key)
    if entry and entry[1] > time.time():
        return entry[0]
    return None


def cache_set(key: str, value, ttl: int = 30):
    _cache[key] = (value, time.time() + ttl)


def init_db():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # SQLite migration: add new columns if they don't exist yet
        from sqlalchemy import text, inspect
        insp = inspect(engine)
        vs_cols = [c["name"] for c in insp.get_columns("voivodeship_statuses")]
        if "error_message" not in vs_cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE voivodeship_statuses ADD COLUMN error_message TEXT DEFAULT ''"))
                conn.commit()
        client_cols = [c["name"] for c in insp.get_columns("clients")]
        if "project_id" not in client_cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE clients ADD COLUMN project_id VARCHAR DEFAULT 'default'"))
                conn.commit()
        order_cols = [c["name"] for c in insp.get_columns("orders")]
        if "project_id" not in order_cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE orders ADD COLUMN project_id VARCHAR DEFAULT 'default'"))
                conn.commit()

        for ind_data in DEFAULT_INDUSTRIES:
            if not db.query(Industry).filter_by(name=ind_data["name"]).first():
                db.add(Industry(**ind_data))
        for v in VOIVODESHIPS:
            if not db.query(VoivodeshipStatus).filter_by(voivodeship=v).first():
                db.add(VoivodeshipStatus(voivodeship=v))
        db.commit()

        # Seed default automations
        from app.models.models import Automation, UserProfile
        _default_automations = [
            {"name": "Auto-przypisz nowego leada", "trigger": "new_lead", "action": "assign"},
            {"name": "Auto-follow-up po 24h", "trigger": "new_lead", "action": "follow_up"},
            {"name": "Priorytetyzuj wysokie score", "trigger": "score_above", "action": "assign", "condition_json": '{"threshold": 70}'},
            {"name": "Auto-oferta dla gorącego leada", "trigger": "score_above", "action": "offer", "condition_json": '{"threshold": 60}'},
            {"name": "Auto-zamknięcie premium", "trigger": "score_above", "action": "close", "condition_json": '{"threshold": 90}'},
            {"name": "Auto-predykcja konwersji", "trigger": "new_lead", "action": "predict"},
        ]
        if db.query(Automation).count() == 0:
            for auto_data in _default_automations:
                db.add(Automation(enabled=True, **auto_data))
            db.commit()
        else:
            # Repair any automations that were seeded with empty names (migration fix)
            unnamed = db.query(Automation).filter(Automation.name == "").all()
            if unnamed:
                for i, auto in enumerate(unnamed):
                    if i < len(_default_automations):
                        auto.name = _default_automations[i]["name"]
                        auto.trigger = _default_automations[i]["trigger"]
                        auto.action = _default_automations[i]["action"]
                db.commit()

        # Seed default users
        if db.query(UserProfile).count() == 0:
            db.add(UserProfile(username="agent1", display_name="Agent Pierwszy", role="agent", email="agent1@auto.pl"))
            db.add(UserProfile(username="agent2", display_name="Agent Drugi", role="agent", email="agent2@auto.pl"))
            db.add(UserProfile(username="manager", display_name="Manager", role="manager", email="manager@auto.pl"))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(application):
    init_db()
    yield


app = FastAPI(
    title="Polska Auto Leads Engine",
    description="Automatyczny system pozyskiwania klientów dla całej Polski — SaaS + mobile + PWA + developer platform.",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Background task references kept to prevent GC
_bg_tasks: set = set()


def _fire_and_forget(coro):
    """Schedule a coroutine and hold a reference to prevent garbage collection."""
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    start = time.perf_counter()
    ip = security.get_client_ip(request)
    endpoint = request.url.path
    user_agent = request.headers.get("user-agent", "")

    if ip in security.BLOCKED_IPS:
        security.add_threat(ip, f"blocked_ip:{security.BLOCKED_IPS[ip]['reason']}", endpoint)
        _fire_and_forget(security.enqueue_audit_log("BLOCKED_IP", ip, user_agent, endpoint))
        devplatform.record_api_request(endpoint, 0)
        return JSONResponse(status_code=403, content={"detail": "IP blocked"})

    if not security.rate_limit_ok(ip):
        security.add_threat(ip, "rate_limit_exceeded", endpoint)
        _fire_and_forget(security.enqueue_audit_log("RATE_LIMITED", ip, user_agent, endpoint))
        devplatform.record_api_request(endpoint, 0)
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    try:
        response = await call_next(request)
    except Exception:
        _fire_and_forget(security.enqueue_audit_log("ERROR_500", ip, user_agent, endpoint))
        devplatform.record_api_request(endpoint, (time.perf_counter() - start) * 1000)
        raise

    action = f"{request.method} {response.status_code}"
    _fire_and_forget(security.enqueue_audit_log(action, ip, user_agent, endpoint))
    devplatform.record_api_request(endpoint, (time.perf_counter() - start) * 1000)
    return response


app.include_router(clients.router)
app.include_router(orders.router)
app.include_router(voivodeships.router)
app.include_router(industries.router)
app.include_router(pipeline.router)
app.include_router(stats.router)
app.include_router(security.router)
app.include_router(analytics.router)
app.include_router(auto_ops.router)
app.include_router(biznes.router)
app.include_router(devplatform.router)
app.include_router(system.router)
app.include_router(leads.router)
app.include_router(campaigns.router)
app.include_router(offers.router)
app.include_router(payments.router)
app.include_router(automations.router)
app.include_router(users.router)
app.include_router(sync.router)


@app.get("/", tags=["system"])
def root():
    return {
        "message": "Polska Auto Leads Engine API",
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "version": APP_VERSION, "ts": int(time.time())}


@app.get("/version", tags=["system"])
def version():
    return {"version": APP_VERSION, "api": "v1"}


@app.get("/metrics", tags=["system"])
def metrics():
    """Pipeline effectiveness metrics."""
    from sqlalchemy.orm import Session
    from app.models.models import Client, Order, AcquisitionLog
    db: Session = SessionLocal()
    try:
        total_clients = db.query(Client).count()
        total_orders = db.query(Order).count()
        total_logs = db.query(AcquisitionLog).count()
        from sqlalchemy import func
        agg = db.query(
            func.sum(AcquisitionLog.found),
            func.sum(AcquisitionLog.accepted),
            func.sum(AcquisitionLog.rejected),
        ).first()
        total_found = int(agg[0] or 0)
        total_accepted = int(agg[1] or 0)
        total_rejected = int(agg[2] or 0)
        acceptance_rate = round(total_accepted / total_found * 100, 1) if total_found else 0
        return {
            "total_clients": total_clients,
            "total_orders": total_orders,
            "pipeline_runs": total_logs,
            "pipeline_found": total_found,
            "pipeline_accepted": total_accepted,
            "pipeline_rejected": total_rejected,
            "acceptance_rate_pct": acceptance_rate,
        }
    finally:
        db.close()


def _fmt_auto(a) -> dict:
    return {"id": a.id, "name": a.name, "trigger": a.trigger, "action": a.action, "runs": a.runs}


@app.get("/report", tags=["system"])
def full_report():
    """Full system status report: API, DB, frontend, automations, endpoints."""
    from sqlalchemy.orm import Session
    from app.models.models import Client, Order, Lead, Campaign, Automation, Payment, Offer, UserProfile
    db: Session = SessionLocal()
    try:
        clients_count = db.query(Client).count()
        orders_count = db.query(Order).count()
        leads_count = db.query(Lead).count()
        campaigns_count = db.query(Campaign).count()
        automations_count = db.query(Automation).filter(Automation.enabled == True).count()
        offers_count = db.query(Offer).count()
        payments_count = db.query(Payment).count()
        users_count = db.query(UserProfile).filter(UserProfile.active == True).count()

        from sqlalchemy import func as sqlfunc
        score_agg = db.query(
            sqlfunc.avg(Lead.score),
            sqlfunc.avg(Lead.conversion_probability),
        ).filter(Lead.stage.not_in(["wygrany", "przegrany"])).first()
        avg_score = round(float(score_agg[0] or 0), 1)
        avg_conv = round(float(score_agg[1] or 0) * 100, 1)

        won_leads = db.query(Lead).filter(Lead.stage == "wygrany").count()
        total_leads = leads_count or 1
        conversion_rate = round(won_leads / total_leads * 100, 1)

        enabled_autos = [_fmt_auto(a) for a in db.query(Automation).filter(Automation.enabled == True).all()]

        endpoints = [
            "GET /", "GET /health", "GET /version", "GET /metrics", "GET /report", "GET /api-config",
            "GET /clients", "POST /clients", "GET /clients/{id}", "PATCH /clients/{id}", "DELETE /clients/{id}",
            "GET /orders", "POST /orders", "GET /orders/{id}", "PATCH /orders/{id}", "DELETE /orders/{id}",
            "GET /leads", "POST /leads", "GET /leads/{id}", "PATCH /leads/{id}", "DELETE /leads/{id}",
            "GET /leads/funnel", "GET /leads/due-follow-ups", "GET /leads/ai-prediction",
            "POST /leads/webhook", "POST /leads/generate-offline",
            "GET /campaigns", "POST /campaigns", "GET /campaigns/{id}", "PATCH /campaigns/{id}", "DELETE /campaigns/{id}",
            "GET /offers", "POST /offers", "PATCH /offers/{id}", "DELETE /offers/{id}",
            "GET /payments", "POST /payments", "PATCH /payments/{id}", "GET /payments/{id}/logs", "POST /payments/{id}/simulate",
            "GET /automations", "POST /automations", "PATCH /automations/{id}", "DELETE /automations/{id}",
            "POST /automations/{id}/run", "POST /automations/run-due-follow-ups", "POST /automations/batch-score",
            "GET /users", "POST /users", "PATCH /users/{id}", "DELETE /users/{id}",
            "GET /stats", "GET /analytics", "GET /pipeline",
            "GET /voivodeships", "GET /industries",
            "POST /sync/auto-backup", "GET /sync/auto-status", "POST /sync/auto-clean",
        ]

        return {
            "status": "ok",
            "version": APP_VERSION,
            "api": {
                "status": "running",
                "endpoints_count": len(endpoints),
                "endpoints": endpoints,
            },
            "database": {
                "status": "ok",
                "clients": clients_count,
                "orders": orders_count,
                "leads": leads_count,
                "campaigns": campaigns_count,
                "offers": offers_count,
                "payments": payments_count,
                "active_users": users_count,
            },
            "automations": {
                "status": "active",
                "enabled_count": automations_count,
                "active_rules": enabled_autos,
            },
            "leads_engine": {
                "total_leads": leads_count,
                "won_leads": won_leads,
                "conversion_rate_pct": conversion_rate,
                "avg_score": avg_score,
                "avg_conversion_pct": avg_conv,
            },
            "frontend": {
                "status": "ok",
                "note": "SPA served at / — panels: Dashboard, Leads, Campaigns, Clients, Orders, Offers, Payments, Automations, Users, Analytics",
            },
        }
    finally:
        db.close()


@app.get("/api-config", tags=["system"])
def api_config(request: Request):
    """Returns the API URL — used by frontend AUTO-CONNECT."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or f"localhost:{API_PORT}"
    scheme = request.headers.get("x-forwarded-proto", "http")
    return {"api_url": f"{scheme}://{host}", "version": APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=False)
