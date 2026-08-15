from __future__ import annotations

import re
from fastapi import APIRouter, HTTPException, Query, Request

from config import TELEGRAM_WEBHOOK_SECRET
from app.pipeline.pipeline import analyze_listing_url
from app.services.telegram import telegram_service

router = APIRouter(prefix="/telegram", tags=["telegram"])

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


@router.post("/webhook")
async def telegram_webhook(request: Request, secret: str = Query(default="")):
    if TELEGRAM_WEBHOOK_SECRET and secret != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    payload = await request.json()
    message = payload.get("message") or {}
    text = message.get("text") or ""
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")

    match = URL_RE.search(text)
    if not match:
        return {"ok": True, "message": "no_url"}

    url = match.group(0)
    try:
        report = analyze_listing_url(url)
        contact = report["contact_phone"] or report["contact_email"] or "W linku"
        budget = f"{report['budget_pln']:.2f} PLN" if isinstance(report["budget_pln"], (int, float)) else "brak danych"
        response_text = (
            "📊 *Raport opłacalności B2B*\n"
            f"• *Tytuł:* {report['title']}\n"
            f"• *Ocena:* {report['lead_score']}/100\n"
            f"• *Budżet:* {budget}\n"
            f"• *FVAT:* {report['vat_required']}\n"
            f"• *Kontakt:* {contact}\n"
            f"• *Tryb/Lokalizacja:* {report['work_mode'] or '-'} | {report['location'] or '-'}"
        )
        keyboard = {
            "inline_keyboard": [[{"text": "Otwórz Zlecenie", "url": report["direct_link"]}]],
        }
        telegram_service.send_message(response_text, chat_id=chat_id, reply_markup=keyboard)
        return {"ok": True, "message": "analyzed"}
    except Exception as exc:
        telegram_service.send_message(f"❌ Nie udało się przeanalizować linku: {exc}", chat_id=chat_id)
        return {"ok": True, "message": "error"}
