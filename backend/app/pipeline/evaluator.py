"""Local zero-cost B2B lead evaluator."""

from __future__ import annotations

import re
from dataclasses import dataclass


PHONE_RE = re.compile(r"(?<!\d)(?:\+?48[\s-]?)?(?:\d[\s-]?){9,11}(?!\d)")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


POSITIVE_KEYWORDS = {
    "faktura vat": 12,
    "b2b": 12,
    "stała współpraca": 10,
    "budżet": 8,
    "dla firmy": 10,
    "długofalowo": 9,
    "agencja": 6,
    "pilne": 7,
    "szukam wykonawcy": 8,
}

NEGATIVE_KEYWORDS = {
    "osoba prywatna": 16,
    "umowa o dzieło": 12,
    "szukam tanio": 15,
    "brak budżetu": 18,
}


@dataclass
class EvaluatedLead:
    score: int
    phone: str
    email: str


class B2BLeadEvaluator:
    def extract_contacts(self, text: str) -> tuple[str, str]:
        phone = ""
        email = ""

        phone_match = PHONE_RE.search(text or "")
        if phone_match:
            phone = re.sub(r"\s+", "", phone_match.group(0))

        email_match = EMAIL_RE.search(text or "")
        if email_match:
            email = email_match.group(0)

        return phone, email

    def score(self, title: str, description: str, vat_required: str = "") -> EvaluatedLead:
        full_text = f"{title} {description}".lower()
        lead_score = 40

        for keyword, weight in POSITIVE_KEYWORDS.items():
            if keyword in full_text:
                lead_score += weight

        for keyword, weight in NEGATIVE_KEYWORDS.items():
            if keyword in full_text:
                lead_score -= weight

        if vat_required.upper() in {"TAK", "YES", "TRUE"}:
            lead_score += 10

        phone, email = self.extract_contacts(full_text)
        if phone:
            lead_score += 7
        if email:
            lead_score += 7

        normalized = max(1, min(100, int(round(lead_score))))
        return EvaluatedLead(score=normalized, phone=phone, email=email)
