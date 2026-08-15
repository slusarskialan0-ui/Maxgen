"""Stealth B2B scraper using curl_cffi for TLS/Cloudflare bypass.

Scrapes B2B job/commission offers from:
  - OLX (Zlecenia / Usługi)
  - Useme
  - Oferteo

Falls back gracefully when curl_cffi is not available or the request fails.
"""
from __future__ import annotations

import json
import logging
import re
import hashlib
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structure returned by all scrapers
# ---------------------------------------------------------------------------

@dataclass
class B2BOrder:
    external_id: str
    title: str
    description: str
    budget: Optional[float]
    fvat_required: bool
    contact_info: dict          # {"phones": [...], "emails": [...]}
    url: str
    source: str
    content_hash: str = field(init=False)

    def __post_init__(self):
        raw = f"{self.title}|{self.url}|{self.source}"
        self.content_hash = hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Shared HTTP helper
# ---------------------------------------------------------------------------

_PHONE_RE = re.compile(r"(?<!\d)(?:\+48\s?)?(?:\d[\s\-]?){9}(?!\d)")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def _extract_contacts(text: str) -> dict:
    phones = list({p.replace(" ", "").replace("-", "") for p in _PHONE_RE.findall(text)})
    emails = list({e.lower() for e in _EMAIL_RE.findall(text)})
    return {"phones": phones[:5], "emails": emails[:5]}


def _try_curl_get(url: str, headers: Optional[dict] = None) -> Optional[str]:
    """Perform a stealth GET using curl_cffi (Chrome120 impersonation).
    Returns raw HTML text or None on failure."""
    try:
        from curl_cffi import requests as curl_requests  # type: ignore
        resp = curl_requests.get(
            url,
            impersonate="chrome120",
            headers=headers or {},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.text
    except ImportError:
        logger.warning("curl_cffi not installed — stealth scraping disabled")
    except Exception as exc:
        logger.warning("curl_cffi GET %s failed: %s", url, exc)
    return None


def _parse_ld_json(html: str) -> list[dict]:
    """Extract all application/ld+json blocks from HTML."""
    results = []
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        try:
            results.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass
    return results


def _parse_prerendered_state(html: str, key: str = "__PRERENDERED_STATE__") -> Optional[dict]:
    """Extract the JS window state object embedded in HTML."""
    pattern = re.compile(
        rf'window\.{re.escape(key)}\s*=\s*(\{{.*?\}});',
        re.DOTALL,
    )
    m = pattern.search(html)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None


def _budget_from_text(text: str) -> Optional[float]:
    """Parse first PLN amount from free text."""
    m = re.search(r"(\d[\d\s]*(?:[,.]\d+)?)\s*(?:zł|PLN|pln)", text, re.IGNORECASE)
    if m:
        raw = m.group(1).replace(" ", "").replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# OLX Zlecenia / Usługi scraper
# ---------------------------------------------------------------------------

_OLX_LISTING_URL = "https://www.olx.pl/uslugi/zlecenia/?search%5Border%5D=created_at:desc"
_OLX_API_URL = "https://www.olx.pl/api/v1/offers/?category_id=322&sort_by=created_at%3Adesc&limit=40&offset=0"


def _scrape_olx() -> list[B2BOrder]:
    orders: list[B2BOrder] = []

    # Try JSON API first (fastest)
    html = _try_curl_get(
        _OLX_API_URL,
        headers={"Accept": "application/json"},
    )
    if html:
        try:
            data = json.loads(html)
            for item in data.get("data", []):
                params = {p["key"]: p["value"]["value"] for p in item.get("params", []) if "value" in p}
                budget_raw = params.get("price") or params.get("budget") or ""
                budget = _budget_from_text(str(budget_raw)) if budget_raw else None
                desc = item.get("description", "")
                url = item.get("url") or f"https://www.olx.pl{item.get('path', '')}"
                fvat = bool(re.search(r"faktura\s*vat|fv\b|vat\b", desc, re.IGNORECASE))
                orders.append(B2BOrder(
                    external_id=str(item.get("id", "")),
                    title=item.get("title", ""),
                    description=desc,
                    budget=budget,
                    fvat_required=fvat,
                    contact_info=_extract_contacts(desc),
                    url=url,
                    source="olx",
                ))
            return orders
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.debug("OLX JSON parse failed: %s — trying HTML", exc)

    # Fallback: HTML listing page
    html = _try_curl_get(_OLX_LISTING_URL)
    if not html:
        return []

    # Try ld+json
    for block in _parse_ld_json(html):
        items = block if isinstance(block, list) else block.get("itemListElement", [])
        for entry in (items if isinstance(items, list) else []):
            item = entry.get("item", entry)
            name = item.get("name", "")
            url = item.get("url", "")
            desc = item.get("description", "")
            if not name or not url:
                continue
            fvat = bool(re.search(r"faktura\s*vat|fv\b|vat\b", desc, re.IGNORECASE))
            orders.append(B2BOrder(
                external_id=hashlib.md5(url.encode()).hexdigest()[:12],
                title=name,
                description=desc,
                budget=_budget_from_text(desc),
                fvat_required=fvat,
                contact_info=_extract_contacts(desc),
                url=url,
                source="olx",
            ))

    return orders


# ---------------------------------------------------------------------------
# Useme scraper
# ---------------------------------------------------------------------------

_USEME_API_URL = "https://useme.com/pl/jobs/?format=json&page_size=40"
_USEME_LISTING_URL = "https://useme.com/pl/jobs/"


def _scrape_useme() -> list[B2BOrder]:
    orders: list[B2BOrder] = []

    html = _try_curl_get(
        _USEME_API_URL,
        headers={"Accept": "application/json"},
    )
    if html:
        try:
            data = json.loads(html)
            results = data.get("results", data if isinstance(data, list) else [])
            for item in results:
                desc = item.get("description", "") or item.get("body", "")
                budget_val = item.get("budget") or item.get("price") or item.get("min_price")
                budget = float(budget_val) if budget_val else _budget_from_text(str(item))
                fvat = bool(re.search(r"faktura\s*vat|fv\b|b2b\b", desc, re.IGNORECASE))
                slug = item.get("slug", "") or str(item.get("id", ""))
                url = item.get("url") or f"https://useme.com/pl/jobs/{slug}/"
                orders.append(B2BOrder(
                    external_id=str(item.get("id", slug)),
                    title=item.get("title", item.get("name", "")),
                    description=desc,
                    budget=budget,
                    fvat_required=fvat,
                    contact_info=_extract_contacts(desc),
                    url=url,
                    source="useme",
                ))
            return orders
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.debug("Useme JSON parse failed: %s — trying HTML", exc)

    html = _try_curl_get(_USEME_LISTING_URL)
    if not html:
        return []

    state = _parse_prerendered_state(html, "__NEXT_DATA__")
    if state:
        try:
            jobs = (
                state.get("props", {})
                     .get("pageProps", {})
                     .get("jobs", [])
            )
            for item in jobs:
                desc = item.get("description", "")
                budget = item.get("budget") or _budget_from_text(desc)
                url = f"https://useme.com/pl/jobs/{item.get('slug', item.get('id', ''))}/"
                fvat = bool(re.search(r"faktura\s*vat|b2b\b", desc, re.IGNORECASE))
                orders.append(B2BOrder(
                    external_id=str(item.get("id", "")),
                    title=item.get("title", ""),
                    description=desc,
                    budget=float(budget) if budget else None,
                    fvat_required=fvat,
                    contact_info=_extract_contacts(desc),
                    url=url,
                    source="useme",
                ))
        except Exception as exc:
            logger.debug("Useme __NEXT_DATA__ parse failed: %s", exc)

    return orders


# ---------------------------------------------------------------------------
# Oferteo scraper
# ---------------------------------------------------------------------------

_OFERTEO_LISTING_URL = "https://oferteo.pl/zlecenia/"


def _scrape_oferteo() -> list[B2BOrder]:
    orders: list[B2BOrder] = []

    html = _try_curl_get(_OFERTEO_LISTING_URL)
    if not html:
        return []

    # Oferteo embeds a JSON state
    for key in ("__PRERENDERED_STATE__", "__NEXT_DATA__", "__NUXT__", "INITIAL_STATE"):
        state = _parse_prerendered_state(html, key)
        if state:
            # Try to find a list of offers anywhere in the structure
            raw = json.dumps(state)
            # Grab all objects with a "title" and "slug"/"id"
            for m in re.finditer(r'\{"id":\s*(\d+).*?"title":\s*"([^"]+)".*?\}', raw):
                ext_id = m.group(1)
                title = m.group(2)
                url = f"https://oferteo.pl/zlecenia/{ext_id}/"
                orders.append(B2BOrder(
                    external_id=ext_id,
                    title=title,
                    description="",
                    budget=None,
                    fvat_required=False,
                    contact_info={"phones": [], "emails": []},
                    url=url,
                    source="oferteo",
                ))
            if orders:
                return orders[:40]

    # Fallback: ld+json
    for block in _parse_ld_json(html):
        for entry in (block if isinstance(block, list) else [block]):
            name = entry.get("name", "")
            url = entry.get("url", "")
            desc = entry.get("description", "")
            if not name:
                continue
            orders.append(B2BOrder(
                external_id=hashlib.md5(url.encode()).hexdigest()[:12],
                title=name,
                description=desc,
                budget=_budget_from_text(desc),
                fvat_required=bool(re.search(r"faktura\s*vat|fv\b", desc, re.IGNORECASE)),
                contact_info=_extract_contacts(desc),
                url=url or _OFERTEO_LISTING_URL,
                source="oferteo",
            ))

    return orders


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrape_b2b_orders() -> list[B2BOrder]:
    """Scrape all configured B2B platforms and return a combined list."""
    results: list[B2BOrder] = []
    for fn, name in [(_scrape_olx, "OLX"), (_scrape_useme, "Useme"), (_scrape_oferteo, "Oferteo")]:
        try:
            orders = fn()
            logger.info("B2B scraper %s: fetched %d orders", name, len(orders))
            results.extend(orders)
        except Exception as exc:
            logger.error("B2B scraper %s raised: %s", name, exc)
    return results


def scrape_single_url(url: str) -> Optional[B2BOrder]:
    """Fetch and parse a single B2B order URL on-demand (for Telegram /check command)."""
    html = _try_curl_get(url)
    if not html:
        return None

    # Detect source from URL using netloc for accurate matching
    from urllib.parse import urlparse as _urlparse
    _netloc = _urlparse(url).netloc.lower()
    if _netloc.endswith("olx.pl") or _netloc == "olx.pl":
        source = "olx"
    elif _netloc.endswith("useme.com") or _netloc == "useme.com":
        source = "useme"
    elif _netloc.endswith("oferteo.pl") or _netloc == "oferteo.pl":
        source = "oferteo"
    else:
        source = "unknown"

    title = ""
    desc = ""
    budget = None
    fvat = False

    # Try ld+json
    for block in _parse_ld_json(html):
        name = block.get("name", "")
        if name:
            title = name
            desc = block.get("description", "")
            budget = _budget_from_text(desc)
            fvat = bool(re.search(r"faktura\s*vat|fv\b|b2b\b", desc, re.IGNORECASE))
            break

    # Fallback: <title> tag
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()

    if not title:
        title = url

    # Try to get description from meta
    if not desc:
        m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html, re.IGNORECASE)
        if m:
            desc = m.group(1)

    budget = budget or _budget_from_text(html[:4000])
    fvat = fvat or bool(re.search(r"faktura\s*vat|fv\b", html[:4000], re.IGNORECASE))

    return B2BOrder(
        external_id=hashlib.md5(url.encode()).hexdigest()[:12],
        title=title,
        description=desc,
        budget=budget,
        fvat_required=fvat,
        contact_info=_extract_contacts(html[:8000]),
        url=url,
        source=source,
    )
