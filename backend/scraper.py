"""Asynchroniczny moduł stealth scrapera B2B dla Polski.

Zwraca listę leadów w formacie:
    [{"title": str, "description": str, "raw_source": {...}}, ...]
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urljoin

from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

LeadDict = dict[str, Any]
Parser = Callable[[str, str], list[LeadDict]]

# 5 branż (niche) do filtrowania leadów.
_BRANCH_KEYWORDS: dict[str, tuple[str, ...]] = {
    "mechanika": ("mechanik", "serwis", "naprawa", "warsztat"),
    "detailing": ("detailing", "polerowanie", "powłoka", "myjnia"),
    "blacharstwo_lakiernictwo": ("blacharz", "lakiernik", "blacharstwo", "lakierowanie"),
    "wulkanizacja": ("wulkanizacja", "opony", "wymiana opon"),
    "transport_i_laweta": ("laweta", "transport aut", "holowanie", "autolaweta"),
}

# Browser fingerprints (Chrome 120+ Windows/macOS)
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_3) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]
_JSON_LD_SCRIPT_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_ANCHOR_RE = re.compile(
    r'<a[^>]+href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<title>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_MAX_RETRY_AFTER_SECONDS = 30.0


@dataclass(slots=True)
class SourceConfig:
    name: str
    url: str
    parser: Parser
    referer: str
    accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


def _build_stealth_headers() -> dict[str, str]:
    ua = random.choice(_USER_AGENTS)
    platform = '"Windows"' if "Windows" in ua else '"macOS"'
    return {
        "User-Agent": ua,
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not:A-Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": platform,
    }


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_id_from_url(url: str) -> str:
    match = re.search(r"(\d{5,})", url)
    if match:
        return match.group(1)
    return re.sub(r"[^a-zA-Z0-9]+", "-", url).strip("-")[:100]


def _is_relevant_branch(text: str) -> bool:
    haystack = text.lower()
    return any(keyword in haystack for keywords in _BRANCH_KEYWORDS.values() for keyword in keywords)


def _unique_key(lead: LeadDict) -> str:
    raw_source = lead.get("raw_source", {})
    source_name = str(raw_source.get("source", "")).strip()
    url = str(raw_source.get("url", "")).strip()
    source_id = str(raw_source.get("id", "")).strip()
    return url or source_id or f"{source_name}|{lead.get('title', '')}|{lead.get('description', '')}"


def _normalize_lead(
    *,
    title: str,
    description: str,
    source_name: str,
    url: str,
    published_at: str | None,
    external_id: str | None = None,
) -> LeadDict | None:
    clean_title = re.sub(r"\s+", " ", (title or "")).strip()
    clean_description = re.sub(r"\s+", " ", (description or "")).strip()
    if not clean_title:
        return None
    if not _is_relevant_branch(f"{clean_title} {clean_description}"):
        return None

    source_url = url.strip() if url else ""
    source_id = (external_id or _extract_id_from_url(source_url) or clean_title[:80]).strip()

    return {
        "title": clean_title,
        "description": clean_description,
        "raw_source": {
            "source": source_name,
            "url": source_url,
            "id": source_id,
            "published_at": published_at or _iso_now(),
        },
    }


def _parse_olx_json(payload: str, source_name: str) -> list[LeadDict]:
    leads: list[LeadDict] = []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return leads
    for item in data.get("data", []):
        item_id = item.get("id")
        lead = _normalize_lead(
            title=item.get("title", ""),
            description=item.get("description", ""),
            source_name=source_name,
            url=item.get("url") or f"https://www.olx.pl{item.get('path', '')}",
            published_at=item.get("created_time") or item.get("created_at"),
            external_id=str(item_id) if item_id is not None else None,
        )
        if lead:
            leads.append(lead)
    return leads


def _parse_useme_json(payload: str, source_name: str) -> list[LeadDict]:
    leads: list[LeadDict] = []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return leads
    items = data.get("results", data if isinstance(data, list) else [])
    for item in items:
        slug = item.get("slug") or item.get("id")
        item_id = item.get("id")
        lead = _normalize_lead(
            title=item.get("title", "") or item.get("name", ""),
            description=item.get("description", "") or item.get("body", ""),
            source_name=source_name,
            url=item.get("url") or f"https://useme.com/pl/jobs/{slug}/",
            published_at=item.get("created") or item.get("published_at"),
            external_id=str(item_id) if item_id is not None else None,
        )
        if lead:
            leads.append(lead)
    return leads


def _parse_json_ld_or_links(payload: str, source_name: str, base_url: str) -> list[LeadDict]:
    leads: list[LeadDict] = []

    for match in _JSON_LD_SCRIPT_RE.finditer(payload):
        try:
            block = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

        elements = block if isinstance(block, list) else block.get("itemListElement") or [block]
        for entry in elements if isinstance(elements, list) else []:
            item = entry.get("item", entry) if isinstance(entry, dict) else {}
            url = item.get("url") or ""
            identifier = item.get("identifier")
            if isinstance(identifier, dict):
                identifier = identifier.get("value") or identifier.get("@id") or identifier.get("id")
            normalized_identifier = None
            if identifier not in (None, "", 0, "0"):
                normalized_identifier = str(identifier)
            lead = _normalize_lead(
                title=item.get("name", "") or item.get("headline", ""),
                description=item.get("description", ""),
                source_name=source_name,
                url=urljoin(base_url, url),
                published_at=item.get("datePublished") or item.get("dateCreated"),
                external_id=normalized_identifier,
            )
            if lead:
                leads.append(lead)

    if leads:
        return leads

    # Fallback parser: anchors that look like tasks/commissions.
    for match in _ANCHOR_RE.finditer(payload):
        raw_title = re.sub(r"<[^>]+>", " ", match.group("title"))
        title = re.sub(r"\s+", " ", raw_title).strip()
        if len(title) < 10:
            continue
        url = urljoin(base_url, match.group("href"))

        lead = _normalize_lead(
            title=title,
            description="",
            source_name=source_name,
            url=url,
            published_at=None,
            external_id=None,
        )
        if lead:
            leads.append(lead)

    return leads


async def _fetch_with_retry(
    session: AsyncSession,
    source: SourceConfig,
    *,
    max_retries: int = 4,
    initial_backoff: float = 1.25,
) -> str:
    headers = _build_stealth_headers()
    headers["Referer"] = source.referer
    headers["Accept"] = source.accept

    backoff = initial_backoff
    for attempt in range(1, max_retries + 1):
        try:
            response = await session.get(source.url, headers=headers, timeout=30)
        except Exception as exc:  # noqa: BLE001
            if attempt < max_retries:
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            raise RuntimeError(f"Source fetch failed for {source.name}: {exc}") from exc

        status_code = response.status_code
        if status_code == 429 or status_code == 408 or status_code >= 500:
            if attempt == max_retries:
                raise RuntimeError(f"HTTP {status_code} for {source.name}")
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                await asyncio.sleep(min(float(retry_after), _MAX_RETRY_AFTER_SECONDS))
            else:
                await asyncio.sleep(backoff)
            backoff *= 2
            continue

        response.raise_for_status()
        return response.text

    raise RuntimeError(f"Source fetch failed for {source.name}")


def _source_configs() -> list[SourceConfig]:
    return [
        SourceConfig(
            name="olx",
            url="https://www.olx.pl/api/v1/offers/?category_id=322&sort_by=created_at%3Adesc&limit=50&offset=0",
            parser=_parse_olx_json,
            referer="https://www.olx.pl/uslugi/zlecenia/",
            accept="application/json,text/plain,*/*",
        ),
        SourceConfig(
            name="useme",
            url="https://useme.com/pl/jobs/?format=json&page_size=50",
            parser=_parse_useme_json,
            referer="https://useme.com/pl/jobs/",
            accept="application/json,text/plain,*/*",
        ),
        SourceConfig(
            name="oferteo",
            url="https://oferteo.pl/zlecenia/warszawa",
            parser=lambda payload, source: _parse_json_ld_or_links(payload, source, "https://oferteo.pl"),
            referer="https://oferteo.pl/",
        ),
        SourceConfig(
            name="oferia",
            url="https://www.oferia.pl/zlecenia/szukaj-warszawa",
            parser=lambda payload, source: _parse_json_ld_or_links(payload, source, "https://www.oferia.pl"),
            referer="https://www.oferia.pl/zlecenia",
        ),
        SourceConfig(
            name="lento",
            url="https://warszawa.lento.pl/motoryzacja/uslugi-i-firmy.html",
            parser=lambda payload, source: _parse_json_ld_or_links(payload, source, "https://warszawa.lento.pl"),
            referer="https://warszawa.lento.pl/",
        ),
    ]


async def _fetch_single_source(session: AsyncSession, source: SourceConfig) -> tuple[SourceConfig, str | None, Exception | None]:
    try:
        payload = await _fetch_with_retry(session, source)
        return source, payload, None
    except Exception as exc:  # noqa: BLE001
        return source, None, exc


async def fetch_latest_b2b_leads() -> list[LeadDict]:
    """Pobiera najnowsze leady B2B z otwartych źródeł i zwraca je bez duplikatów.

    Funkcja jest odporna na błędy źródeł (429/503/5xx):
    - stosuje retry z exponential backoff,
    - po wyczerpaniu prób loguje błąd i kontynuuje kolejne źródła.
    """
    results: list[LeadDict] = []
    seen: set[str] = set()

    async with AsyncSession(impersonate="chrome124", verify=True) as session:
        source_results = await asyncio.gather(
            *[_fetch_single_source(session, source) for source in _source_configs()]
        )

        for source, payload, error in source_results:
            if error is not None or payload is None:
                logger.warning("Scraper source failed: %s (%s)", source.name, error)
                continue

            try:
                parsed = source.parser(payload, source.name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Scraper parser failed: %s (%s)", source.name, exc)
                continue
            for lead in parsed:
                key = _unique_key(lead)
                if key in seen:
                    continue
                seen.add(key)
                results.append(lead)

    return results


__all__ = ["fetch_latest_b2b_leads"]
