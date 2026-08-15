"""Setup wizard API — save config, test Telegram, test DB, status."""
from __future__ import annotations

import logging
import os
import time

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import build_db_connect_args, normalize_database_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/setup", tags=["setup"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SaveConfigRequest(BaseModel):
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    DATABASE_URL: str = ""
    B2B_LEAD_SCORE_THRESHOLD: str = ""


class TestTelegramRequest(BaseModel):
    token: str
    chat_id: str


class TestDbRequest(BaseModel):
    database_url: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db():
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _upsert_config(key: str, value: str) -> None:
    from database import SessionLocal
    from app.models.models import SystemConfig
    db = SessionLocal()
    try:
        row = db.query(SystemConfig).filter_by(key=key).first()
        if row:
            row.value = value
        else:
            db.add(SystemConfig(key=key, value=value))
        db.commit()
    finally:
        db.close()


def _read_config(key: str, default: str = "") -> str:
    try:
        from database import SessionLocal
        from app.models.models import SystemConfig
        db = SessionLocal()
        try:
            row = db.query(SystemConfig).filter_by(key=key).first()
            return row.value if row else os.getenv(key, default)
        finally:
            db.close()
    except Exception:
        return os.getenv(key, default)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/save")
async def save_config(body: SaveConfigRequest):
    """Persist configuration to DB (and optionally OS env) without restart."""
    saved = []
    for field_name, value in body.model_dump().items():
        if value:
            if field_name == "DATABASE_URL":
                value = normalize_database_url(value)
            _upsert_config(field_name, value)
            # Also update running process env so immediate effect
            os.environ[field_name] = value
            saved.append(field_name)
    return {"status": "saved", "keys": saved}


@router.post("/test-telegram")
async def test_telegram(body: TestTelegramRequest):
    """Send a test message via Telegram Bot API and validate the token."""
    if not body.token or not body.chat_id:
        raise HTTPException(status_code=400, detail="token and chat_id are required")

    url = f"https://api.telegram.org/bot{body.token}/sendMessage"
    payload = {
        "chat_id": body.chat_id,
        "text": (
            "✅ <b>Polska Auto Leads Engine</b>\n\n"
            "Połączenie z Telegramem działa poprawnie! 🎉\n"
            "Bot jest gotowy do wysyłania alertów B2B."
        ),
        "parse_mode": "HTML",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Cannot reach Telegram API: {exc}")

    if not data.get("ok"):
        raise HTTPException(
            status_code=400,
            detail=data.get("description", "Telegram API returned error"),
        )

    # Persist if test passes
    _upsert_config("TELEGRAM_BOT_TOKEN", body.token)
    _upsert_config("TELEGRAM_CHAT_ID", body.chat_id)
    os.environ["TELEGRAM_BOT_TOKEN"] = body.token
    os.environ["TELEGRAM_CHAT_ID"] = body.chat_id

    return {"status": "ok", "message": "Test message sent successfully"}


@router.post("/test-db")
async def test_db(body: TestDbRequest):
    """Test PostgreSQL/SQLite connection and run table migrations."""
    if not body.database_url:
        raise HTTPException(status_code=400, detail="database_url is required")

    db_url = normalize_database_url(body.database_url)
    connect_args = build_db_connect_args(db_url)

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # Run migrations on the new DB
        from database import Base
        from app.models import models as _models_module  # noqa: F401 — ensure all models are registered
        Base.metadata.create_all(bind=engine)

        # Persist
        _upsert_config("DATABASE_URL", db_url)
        os.environ["DATABASE_URL"] = db_url

        return {"status": "ok", "message": "Database connected and migrations applied"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Database connection failed: {exc}")


@router.get("/status")
async def setup_status():
    """Return current configuration status (sensitive values masked)."""
    def _mask(val: str) -> str:
        if not val:
            return ""
        return val[:4] + "****" + val[-4:] if len(val) > 8 else "****"

    token = _read_config("TELEGRAM_BOT_TOKEN")
    chat  = _read_config("TELEGRAM_CHAT_ID")
    db_url = _read_config("DATABASE_URL", os.getenv("DATABASE_URL", ""))
    threshold = _read_config("B2B_LEAD_SCORE_THRESHOLD", "65")

    return {
        "telegram": {
            "configured": bool(token and chat),
            "token_masked": _mask(token),
            "chat_id_masked": _mask(chat),
        },
        "database": {
            "configured": bool(db_url),
            "type": "postgresql" if "postgresql" in db_url or "postgres" in db_url else "sqlite",
            "url_masked": _mask(db_url),
        },
        "b2b_scanner": {
            "score_threshold": int(threshold) if threshold else 65,
        },
    }
