"""B2B listing sources fetched with curl_cffi and JSON-first parsing."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from curl_cffi import requests

from config import B2B_SCRAPER_TIMEOUT
from app.pipeline.evaluator import B2BLeadEvaluator

logger = logging.getLogger(__name__)

WINDOW_STATE_RE = re.compile(
    r"window\.__PRERENDERED_STATE__\s*=\s*(\{.*?\});",
    re.DOTALL,
)
JSON_SCRIPT_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class B2BLeadCandidate:
    source_name: str
    external_id: str
    title: str
    budget_pln: float | None
    vat_required: str
    description: str
    contact_phone: str
    contact_email: str
    location: str
    work_mode: str
    direct_link: str
    lead_score: int
    raw_payload: dict[str, Any]


class CurlCffiB2BSource:
    def __init__(self, source_name: str, endpoints: list[str]):
        self.source_name = source_name
        self.endpoints = endpoints
        self._session = requests.Session()
        self._evaluator = B2BLeadEvaluator()

    def fetch_from_url(self, url: str) -> list[B2BLeadCandidate]:
        resp = self._session.get(
            url,
            timeout=B2B_SCRAPER_TIMEOUT,
            impersonate="chrome120",
            allow_redirects=True,
            headers={"Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8"},
        )
        resp.raise_for_status()
        return self.parse_html(resp.text, base_url=url)

    def parse_html(self, html: str, base_url: str = "") -> list[B2BLeadCandidate]:
        records: list[dict[str, Any]] = []

        for payload in self._extract_ld_json(html):
            records.extend(self._flatten_objects(payload))

        window_state = self._extract_window_state(html)
        if window_state:
            records.extend(self._flatten_objects(window_state))

        unique: dict[str, B2BLeadCandidate] = {}
        for raw in records:
            lead = self._to_lead(raw, base_url)
            if not lead:
                continue
            key = lead.external_id or lead.direct_link or lead.title
            if key not in unique:
                unique[key] = lead

        return list(unique.values())

    def _extract_ld_json(self, html: str) -> list[Any]:
        payloads: list[Any] = []
        for block in JSON_SCRIPT_RE.findall(html or ""):
            data = block.strip()
            if not data:
                continue
            try:
                payloads.append(json.loads(data))
            except json.JSONDecodeError:
                continue
        return payloads

    def _extract_window_state(self, html: str) -> dict[str, Any] | None:
        match = WINDOW_STATE_RE.search(html or "")
        if not match:
            return None
        payload = match.group(1)
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None

    def _flatten_objects(self, item: Any) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if isinstance(item, dict):
            result.append(item)
            for value in item.values():
                result.extend(self._flatten_objects(value))
        elif isinstance(item, list):
            for child in item:
                result.extend(self._flatten_objects(child))
        return result

    def _to_lead(self, payload: dict[str, Any], fallback_link: str) -> B2BLeadCandidate | None:
        title = (
            payload.get("title")
            or payload.get("name")
            or payload.get("headline")
            or payload.get("subject")
            or ""
        )
        description = (
            payload.get("description")
            or payload.get("body")
            or payload.get("content")
            or payload.get("details")
            or ""
        )
        if not title or not description:
            return None

        external_id = str(payload.get("id") or payload.get("offerId") or payload.get("jobId") or "")
        direct_link = (
            payload.get("url")
            or payload.get("link")
            or payload.get("canonicalUrl")
            or fallback_link
            or ""
        )
        if not direct_link:
            return None

        budget = self._extract_budget(payload)
        vat_required = self._extract_vat(payload, description)
        location = self._extract_location(payload)
        work_mode = self._extract_work_mode(payload, description)

        evaluated = self._evaluator.score(title=title, description=description, vat_required=vat_required)
        phone = evaluated.phone
        email = evaluated.email

        if not phone:
            phone = str(payload.get("phone") or payload.get("telephone") or "")
        if not email:
            email = str(payload.get("email") or "")

        return B2BLeadCandidate(
            source_name=self.source_name,
            external_id=external_id,
            title=str(title).strip(),
            budget_pln=budget,
            vat_required=vat_required,
            description=str(description).strip(),
            contact_phone=phone.strip(),
            contact_email=email.strip(),
            location=location,
            work_mode=work_mode,
            direct_link=str(direct_link).strip(),
            lead_score=evaluated.score,
            raw_payload=payload,
        )

    @staticmethod
    def _extract_budget(payload: dict[str, Any]) -> float | None:
        offers = payload.get("offers")
        candidates = [
            payload.get("budget"),
            payload.get("price"),
            payload.get("value"),
            payload.get("amount"),
        ]
        if isinstance(offers, dict):
            candidates += [offers.get("price"), offers.get("priceSpecification")]

        for item in candidates:
            if isinstance(item, dict):
                item = item.get("price") or item.get("minPrice") or item.get("maxPrice")
            if item is None:
                continue
            match = re.search(r"\d+[\d\s,.]*", str(item))
            if not match:
                continue
            normalized = match.group(0).replace(" ", "").replace(",", ".")
            try:
                return float(normalized)
            except ValueError:
                continue
        return None

    @staticmethod
    def _extract_vat(payload: dict[str, Any], description: str) -> str:
        direct = str(payload.get("vat") or payload.get("invoice") or payload.get("faktura") or "").lower()
        merged = f"{direct} {description}".lower()
        if "faktura vat" in merged or "vat required" in merged or "vat" in direct:
            return "TAK"
        if "bez vat" in merged or "nie wymaga vat" in merged:
            return "NIE"
        return "BRAK DANYCH"

    @staticmethod
    def _extract_location(payload: dict[str, Any]) -> str:
        location = payload.get("location") or payload.get("address") or payload.get("jobLocation")
        if isinstance(location, dict):
            parts = [
                location.get("name"),
                location.get("city"),
                location.get("addressLocality"),
                location.get("region"),
            ]
            return ", ".join([str(p).strip() for p in parts if p])
        if isinstance(location, str):
            return location.strip()
        return ""

    @staticmethod
    def _extract_work_mode(payload: dict[str, Any], description: str) -> str:
        mode = str(payload.get("workMode") or payload.get("employmentType") or "")
        merged = f"{mode} {description}".lower()
        if any(k in merged for k in ["zdal", "remote"]):
            return "Zdalnie"
        if any(k in merged for k in ["stacjon", "on-site", "onsite"]):
            return "Stacjonarnie"
        return ""


def build_sources() -> list[CurlCffiB2BSource]:
    from config import B2B_SCRAPER_URLS

    if not B2B_SCRAPER_URLS:
        return []
    return [CurlCffiB2BSource(source_name="b2b_marketplaces", endpoints=B2B_SCRAPER_URLS)]
