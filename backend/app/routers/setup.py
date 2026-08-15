import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from app.models.models import Base

router = APIRouter(prefix="/api/setup", tags=["setup"])


class TelegramSetupPayload(BaseModel):
    telegram_bot_token: str = Field(..., min_length=1)
    telegram_chat_id: str = Field(..., min_length=1)


class DbSetupPayload(BaseModel):
    database_url: str = Field(..., min_length=1)


@router.post("/test-telegram")
def test_telegram(payload: TelegramSetupPayload):
    token = payload.telegram_bot_token.strip()
    chat_id = payload.telegram_chat_id.strip()
    message = f"✅ Test alert z Polska Auto Leads Engine MAX ({datetime.now(timezone.utc).isoformat()})"
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")

    try:
        with urlopen(api_url, data=body, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Nie udało się wysłać alertu Telegram: {exc}")

    if not data.get("ok"):
        description = data.get("description") or "Nieznany błąd Telegram API"
        raise HTTPException(status_code=400, detail=description)

    return {"ok": True, "status": "telegram_test_sent", "message": "Wysłano testowy alert Telegram."}


@router.post("/test-db")
def test_db(payload: DbSetupPayload):
    database_url = payload.database_url.strip()
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

    try:
        test_engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=test_engine)
        test_engine.dispose()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Połączenie z bazą nieudane: {exc}")

    return {"ok": True, "status": "db_connected", "message": "Połączenie z bazą jest poprawne, tabele zostały zweryfikowane."}
