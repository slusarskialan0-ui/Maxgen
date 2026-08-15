"""Telegram Bot Command Center for B2B Lead Engine.

Features:
  - PUSH alerts for B2B leads with LeadScore >= threshold
    with Inline buttons: [📥 Open] [✉️ Quick Reply]
  - /check <url>  — instantly analyses any B2B order URL
  - /status       — returns scanner status
  - /help         — usage guide
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config helpers (read from DB at runtime so no restart is needed)
# ---------------------------------------------------------------------------

def _get_telegram_config() -> tuple[str, str]:
    """Return (bot_token, chat_id) from DB SystemConfig, falling back to env."""
    try:
        from database import SessionLocal
        from app.models.models import SystemConfig
        db = SessionLocal()
        try:
            token_row = db.query(SystemConfig).filter_by(key="TELEGRAM_BOT_TOKEN").first()
            chat_row  = db.query(SystemConfig).filter_by(key="TELEGRAM_CHAT_ID").first()
            token = (token_row.value if token_row else "") or os.getenv("TELEGRAM_BOT_TOKEN", "")
            chat  = (chat_row.value  if chat_row  else "") or os.getenv("TELEGRAM_CHAT_ID",  "")
            return token, chat
        finally:
            db.close()
    except Exception:
        return os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")


# ---------------------------------------------------------------------------
# Core send helpers
# ---------------------------------------------------------------------------

async def _tg_request(token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def send_message(token: str, chat_id: str, text: str, reply_markup: Optional[dict] = None) -> dict:
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await _tg_request(token, "sendMessage", payload)


async def answer_callback_query(token: str, callback_query_id: str, text: str = "") -> dict:
    return await _tg_request(token, "answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text,
    })


# ---------------------------------------------------------------------------
# PUSH alert builder
# ---------------------------------------------------------------------------

def _format_lead_alert(lead) -> str:
    """Format a B2BLead DB object as a Telegram HTML message."""
    budget_str = f"{lead.budget:,.0f} PLN" if lead.budget else "nieznany"
    fvat_str = "✅ TAK" if lead.fvat_required else "❌ NIE"

    try:
        ci = json.loads(lead.contact_info) if isinstance(lead.contact_info, str) else (lead.contact_info or {})
    except Exception:
        ci = {}

    phones = ", ".join(ci.get("phones", [])) or "—"
    emails = ", ".join(ci.get("emails", [])) or "—"

    return (
        f"🎯 <b>Nowe zlecenie B2B</b>  |  Score: <b>{lead.score}/100</b>\n\n"
        f"📌 <b>{lead.title}</b>\n\n"
        f"💰 Budżet: {budget_str}\n"
        f"🧾 Faktura VAT: {fvat_str}\n"
        f"📞 Tel: {phones}\n"
        f"📧 Email: {emails}\n\n"
        f"🔗 Źródło: {lead.source.upper()}"
    )


def _lead_keyboard(lead_url: str) -> dict:
    return {
        "inline_keyboard": [[
            {"text": "📥 Otwórz Zlecenie", "url": lead_url},
            {"text": "✉️ Szybka Odpowiedź", "callback_data": f"reply:{lead_url}"},
        ]]
    }


async def push_lead_alert(lead) -> bool:
    """Send a PUSH alert to Telegram for a B2BLead. Returns True on success."""
    token, chat_id = _get_telegram_config()
    if not token or not chat_id:
        logger.warning("Telegram not configured — skipping push alert")
        return False
    try:
        await send_message(
            token, chat_id,
            _format_lead_alert(lead),
            reply_markup=_lead_keyboard(lead.url),
        )
        return True
    except Exception as exc:
        logger.error("Telegram push_lead_alert failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# FastAPI router — webhook / polling endpoint
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[dict] = None
    callback_query: Optional[dict] = None


@router.post("/webhook")
async def telegram_webhook(update: TelegramUpdate, background: BackgroundTasks):
    """Receive updates from Telegram (set webhook URL to /api/telegram/webhook)."""
    token, _ = _get_telegram_config()
    if not token:
        raise HTTPException(status_code=503, detail="Telegram not configured")

    background.add_task(_handle_update, token, update.model_dump())
    return {"ok": True}


async def _handle_update(token: str, update: dict) -> None:
    try:
        message = update.get("message") or {}
        callback = update.get("callback_query") or {}

        # Handle callback query (inline button press)
        if callback:
            cb_id = callback.get("id", "")
            data = callback.get("data", "")
            msg = callback.get("message") or {}
            chat_id = str((msg.get("chat") or {}).get("id", ""))
            if data.startswith("reply:"):
                url = data[6:]
                reply_text = (
                    "✉️ <b>Szablon szybkiej odpowiedzi:</b>\n\n"
                    "Dzień dobry,\n\n"
                    "Widziałem Państwa zlecenie i chciałbym zaproponować współpracę. "
                    "Mam doświadczenie w tej dziedzinie i mogę zrealizować projekt "
                    "w terminie i budżecie.\n\n"
                    f"🔗 Zlecenie: {url}\n\n"
                    "Proszę o kontakt. Pozdrawiam,"
                )
                await send_message(token, chat_id, reply_text)
                await answer_callback_query(token, cb_id, "Szablon gotowy!")
            return

        # Handle regular text messages
        chat_id = str((message.get("chat") or {}).get("id", ""))
        text = (message.get("text") or "").strip()
        if not text or not chat_id:
            return

        if text.startswith("/help") or text == "/start":
            await send_message(token, chat_id,
                "🤖 <b>B2B Lead Engine Bot</b>\n\n"
                "Dostępne komendy:\n"
                "/check &lt;url&gt; — analiza zlecenia B2B\n"
                "/status — status skanera\n"
                "/help — ta wiadomość\n\n"
                "Możesz też wkleić dowolny link ze zleceniem B2B — bot automatycznie go przeanalizuje."
            )

        elif text.startswith("/status"):
            from database import SessionLocal
            from app.models.models import B2BLead, SystemConfig
            db = SessionLocal()
            try:
                total = db.query(B2BLead).count()
                scanner_row = db.query(SystemConfig).filter_by(key="b2b_scanner_enabled").first()
                scanner_on = scanner_row.value == "true" if scanner_row else False
                status_icon = "🟢" if scanner_on else "🔴"
                await send_message(token, chat_id,
                    f"{status_icon} <b>Status skanera B2B</b>\n\n"
                    f"Skaner: {'AKTYWNY' if scanner_on else 'ZATRZYMANY'}\n"
                    f"Łącznie leadów w bazie: {total}"
                )
            finally:
                db.close()

        elif text.startswith("/check ") or text.startswith("http"):
            url = text.replace("/check ", "").strip()
            if not url.startswith("http"):
                await send_message(token, chat_id, "❌ Podaj pełny URL (zaczynający się od http)")
                return
            await send_message(token, chat_id, "⏳ Analizuję zlecenie...")
            await _analyse_url_and_reply(token, chat_id, url)

        else:
            # Check if the message contains a URL
            import re
            url_m = re.search(r"https?://\S+", text)
            if url_m:
                url = url_m.group(0)
                await send_message(token, chat_id, "⏳ Analizuję zlecenie...")
                await _analyse_url_and_reply(token, chat_id, url)

    except Exception as exc:
        logger.error("_handle_update error: %s", exc)


async def _analyse_url_and_reply(token: str, chat_id: str, url: str) -> None:
    """Fetch a B2B order URL, score it, and send analysis back to user."""
    from app.sources.b2b_scraper import scrape_single_url
    from app.pipeline.b2b_scorer import compute_lead_score

    order = scrape_single_url(url)
    if not order:
        await send_message(token, chat_id, "❌ Nie udało się pobrać strony. Spróbuj ponownie.")
        return

    score = compute_lead_score(
        title=order.title,
        description=order.description,
        budget=order.budget,
        fvat_required=order.fvat_required,
        source=order.source,
        contact_info=order.contact_info,
    )

    ci = order.contact_info or {}
    phones = ", ".join(ci.get("phones", [])) or "—"
    emails = ", ".join(ci.get("emails", [])) or "—"
    budget_str = f"{order.budget:,.0f} PLN" if order.budget else "nieznany"
    fvat_str = "✅ TAK" if order.fvat_required else "❌ NIE"
    verdict = "🔥 GORĄCY LEAD" if score >= 65 else ("⚠️ ŚREDNI" if score >= 40 else "❄️ SŁABY")

    text = (
        f"📊 <b>Raport opłacalności</b>\n\n"
        f"📌 <b>{order.title}</b>\n\n"
        f"🎯 LeadScore: <b>{score}/100</b>  {verdict}\n"
        f"💰 Budżet: {budget_str}\n"
        f"🧾 Faktura VAT: {fvat_str}\n"
        f"📞 Tel: {phones}\n"
        f"📧 Email: {emails}\n\n"
        f"📝 <i>{order.description[:300]}{'...' if len(order.description) > 300 else ''}</i>"
    )
    await send_message(token, chat_id, text, reply_markup=_lead_keyboard(url))
