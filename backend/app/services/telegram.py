"""Telegram notifications and command center helpers."""

from __future__ import annotations

import logging
from typing import Any

from curl_cffi import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str, chat_id: str | None = None, reply_markup: dict[str, Any] | None = None) -> bool:
        target_chat = chat_id or self.chat_id
        if not self.bot_token or not target_chat:
            return False

        payload: dict[str, Any] = {
            "chat_id": target_chat,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json=payload,
                timeout=15,
                impersonate="chrome120",
            )
            resp.raise_for_status()
            return bool(resp.json().get("ok"))
        except Exception as exc:
            logger.warning("Telegram send failed: %s", exc)
            return False

    def send_lead_alert(self, lead) -> bool:
        contact = lead.contact_phone or lead.contact_email or "W linku"
        budget = f"{lead.budget_pln:.2f} PLN" if isinstance(lead.budget_pln, (int, float)) else "brak danych"
        message = (
            "🎯 *NOWY LEAD B2B / ZLECENIE*\n"
            f"• *Tytuł:* {lead.title}\n"
            f"• *Budżet:* {budget} | *FVAT:* {lead.vat_required}\n"
            f"• *Kontakt:* {contact}\n"
            f"• *Ocena:* {lead.lead_score}/100"
        )
        keyboard = {
            "inline_keyboard": [[{"text": "Otwórz Zlecenie", "url": lead.direct_link}]],
        }
        return self.send_message(message, reply_markup=keyboard)


telegram_service = TelegramService()
