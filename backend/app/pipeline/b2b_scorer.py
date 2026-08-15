"""Heuristic B2B Lead Scorer with deduplication.

LeadScore (1-100) is computed locally without any external AI service:
  - Keyword boosts  (up to +50 pts)
  - Budget presence (up to +20 pts)
  - FVat required   (       +10 pts)
  - Source trust    (up to  + 5 pts)
  - Contact info    (up to  + 5 pts)
  - Penalties for private / no-budget posts
"""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword tables
# ---------------------------------------------------------------------------

_BOOST_KEYWORDS: list[tuple[str, int]] = [
    ("faktura vat", 15),
    ("b2b", 12),
    ("stała współpraca", 12),
    ("długoterminowa", 10),
    ("budżet", 10),
    ("dla firmy", 8),
    ("pilne", 8),
    ("agencja", 7),
    ("firma", 6),
    ("zlecenie cykliczne", 10),
    ("umowa", 6),
    ("nip", 5),
    ("regon", 5),
    ("korporacja", 5),
    ("przetarg", 5),
    ("kontrakt", 8),
    ("monthly retainer", 8),
    ("retainer", 6),
    ("co miesiąc", 5),
    ("abonament", 5),
]

_PENALTY_KEYWORDS: list[tuple[str, int]] = [
    ("osoba prywatna", -15),
    ("amator", -10),
    ("hobby", -10),
    ("dla siebie", -12),
    ("bez faktury", -12),
    ("nie wystawiam faktury", -15),
    ("studencki", -8),
]

_SOURCE_TRUST: dict[str, int] = {
    "useme": 5,
    "oferteo": 4,
    "olx": 3,
    "unknown": 1,
}


def compute_lead_score(
    title: str,
    description: str,
    budget: Optional[float],
    fvat_required: bool,
    source: str,
    contact_info: Optional[dict] = None,
) -> int:
    """Return a LeadScore integer between 1 and 100."""
    text = f"{title} {description}".lower()
    score = 20  # base

    # Keyword boost
    for kw, pts in _BOOST_KEYWORDS:
        if kw in text:
            score += pts

    # Keyword penalties
    for kw, pts in _PENALTY_KEYWORDS:
        if kw in text:
            score += pts  # pts are negative

    # Budget
    if budget and budget > 0:
        if budget >= 5000:
            score += 20
        elif budget >= 1000:
            score += 12
        elif budget >= 300:
            score += 6
        else:
            score += 3
    else:
        score -= 5

    # FVat
    if fvat_required:
        score += 10

    # Source trust
    score += _SOURCE_TRUST.get(source, 1)

    # Contact info
    ci = contact_info or {}
    if ci.get("phones"):
        score += 3
    if ci.get("emails"):
        score += 2

    return max(1, min(100, score))


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _title_fingerprint(title: str) -> str:
    """Normalise title for fuzzy matching."""
    import re
    return re.sub(r"\s+", " ", title.lower().strip())


def deduplicate_orders(
    new_orders,
    existing_hashes: set[str],
    existing_titles: list[str],
    fuzzy_threshold: int = 85,
) -> list:
    """Return only orders that are not duplicates.

    :param new_orders: list of B2BOrder objects
    :param existing_hashes: set of content_hash strings already in DB
    :param existing_titles: list of titles already in DB (for fuzzy matching)
    :param fuzzy_threshold: minimum Levenshtein similarity ratio (0-100)
    """
    try:
        from thefuzz import fuzz  # type: ignore
        _fuzz_available = True
    except ImportError:
        _fuzz_available = False
        logger.warning("thefuzz not available — fuzzy dedup disabled")

    unique: list = []
    seen_hashes: set[str] = set(existing_hashes)
    seen_titles: list[str] = list(existing_titles)

    for order in new_orders:
        # Hash dedup
        if order.content_hash in seen_hashes:
            logger.debug("Dedup (hash): %s", order.title[:60])
            continue

        # Fuzzy title dedup
        if _fuzz_available:
            fp = _title_fingerprint(order.title)
            is_dup = False
            for existing_title in seen_titles:
                ratio = fuzz.token_set_ratio(fp, _title_fingerprint(existing_title))
                if ratio >= fuzzy_threshold:
                    logger.debug("Dedup (fuzzy %d%%): %s", ratio, order.title[:60])
                    is_dup = True
                    break
            if is_dup:
                continue

        unique.append(order)
        seen_hashes.add(order.content_hash)
        seen_titles.append(order.title)

    return unique
