"""Offline helpers for scoring, seeded generation and content."""
from __future__ import annotations

import hashlib
import random


def seeded_rng(*parts: str) -> random.Random:
    raw = "|".join(parts)
    seed = int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def score_lead(email: str = "", phone: str = "", company: str = "", industry: str = "", voivodeship: str = "") -> float:
    score = 15.0
    score += 20 if email else 0
    score += 15 if phone else 0
    score += 10 if company else 0
    score += 10 if industry else 0
    score += 5 if voivodeship else 0
    if email.endswith(".pl"):
        score += 5
    if phone.startswith("+48"):
        score += 5
    return round(min(100.0, score), 1)


def conversion_probability(score: float, stage: str) -> float:
    stage_weight = {
        "nowy": 0.08,
        "kontakt": 0.25,
        "negocjacje": 0.55,
        "wygrany": 1.0,
        "przegrany": 0.0,
    }.get(stage, 0.1)
    return round(min(1.0, max(0.0, stage_weight * 0.6 + (score / 100.0) * 0.4)), 3)


def generate_offer_content(company: str, industry: str, amount: float) -> str:
    return (
        f"Oferta offline dla {company or 'Klienta'}\n"
        f"Branża: {industry or 'ogólna'}\n"
        f"Zakres: pozyskiwanie leadów, kampanie, follow-up i dashboard konwersji.\n"
        f"Cena pakietu: {amount:.2f} PLN\n"
        "Wersja oferty: offline-v1"
    )


def marketing_copy(campaign_name: str, industry: str) -> dict:
    rng = seeded_rng(campaign_name or "kampania", industry or "branza")
    hooks = [
        "Zdobądź więcej klientów lokalnie",
        "Automatyzuj sprzedaż bez kosztownych integracji",
        "Skaluj leady offline i kontroluj każdy etap lejka",
    ]
    ctas = ["Umów demo", "Sprawdź ofertę", "Uruchom kampanię teraz"]
    desc = [
        "Kompletny system leadów, kampanii i ofert działający offline.",
        "Silnik sprzedaży z automatyzacją follow-up i scoringiem.",
        "Jedna platforma do leadów, konwersji i przychodów.",
    ]
    return {
        "headline": hooks[rng.randrange(len(hooks))],
        "cta": ctas[rng.randrange(len(ctas))],
        "description": desc[rng.randrange(len(desc))],
    }
