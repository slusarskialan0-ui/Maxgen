"""Real API source integrations with offline fallback.

When API credentials are missing or the API is unreachable the source
transparently falls back to the mock generator from sources.py so the
pipeline continues to work without any external dependencies.

Environment variables expected:
    FACEBOOK_ACCESS_TOKEN    — Facebook Graph API long-lived page/app token
    LINKEDIN_ACCESS_TOKEN    — LinkedIn OAuth2 bearer token
    GOOGLE_MAPS_API_KEY      — Google Places / Maps API key
    CEIDG_API_KEY            — CEIDG (Central Business Register) API key
"""
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

from curl_cffi import requests

from .base import BaseSource, CompanyProfile
from .sources import _generate_profiles
from ..pipeline.retry_handler import RateLimiter, retry, SOURCE_TIMEOUT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared HTTP helpers
# ---------------------------------------------------------------------------

_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "PolskaAutoLeadsEngine/3.0"


def _get(url: str, params: Optional[dict] = None, headers: Optional[dict] = None, timeout: int = SOURCE_TIMEOUT) -> Any:
    """Perform a GET request and return parsed JSON body."""
    resp = _SESSION.get(
        url,
        params=params,
        headers=headers,
        timeout=timeout,
        impersonate="chrome120",
        allow_redirects=True,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Facebook Graph API
# ---------------------------------------------------------------------------

_FB_RATE_LIMITER = RateLimiter(max_calls=5, period=1.0)


class FacebookSource(BaseSource):
    """Fetch business pages via Facebook Graph API.

    Falls back to synthetic mock data when FACEBOOK_ACCESS_TOKEN is absent or
    when the API call fails.
    """

    source_type = "social"
    source_detail = "Facebook Graph API"

    def __init__(self) -> None:
        self._token = os.getenv("FACEBOOK_ACCESS_TOKEN", "")

    @retry(max_attempts=3, initial_delay=2.0)
    def _search_pages(self, query: str) -> list[dict]:
        _FB_RATE_LIMITER.acquire()
        data = _get(
            "https://graph.facebook.com/v19.0/search",
            params={
                "q": query,
                "type": "page",
                "fields": "name,emails,phone,website,location",
                "access_token": self._token,
            },
        )
        return data.get("data", [])

    def fetch(self, voivodeship: str, industries: list[str]) -> list[CompanyProfile]:
        if not self._token:
            logger.debug("FacebookSource: no token, using mock fallback")
            return _generate_profiles(voivodeship, industries, self.source_type, self.source_detail, count_per_industry=4)

        profiles: list[CompanyProfile] = []
        for industry in industries:
            try:
                pages = self._search_pages(f"{industry} {voivodeship}")
                for page in pages[:5]:
                    location = page.get("location") or {}
                    profiles.append(
                        CompanyProfile(
                            company_name=page.get("name", ""),
                            industry=industry,
                            voivodeship=voivodeship,
                            city=location.get("city", ""),
                            county=location.get("state", ""),
                            email=(page.get("emails") or [""])[0],
                            phone=page.get("phone", ""),
                            website=page.get("website", ""),
                            source_type=self.source_type,
                            source_detail=self.source_detail,
                            acquired_at=datetime.now(timezone.utc),
                        )
                    )
            except Exception as exc:
                logger.warning("FacebookSource fetch error for %s/%s: %s — using mock fallback", voivodeship, industry, exc)
                profiles.extend(
                    _generate_profiles(voivodeship, [industry], self.source_type, self.source_detail, count_per_industry=4)
                )
        return profiles


# ---------------------------------------------------------------------------
# LinkedIn API
# ---------------------------------------------------------------------------

_LI_RATE_LIMITER = RateLimiter(max_calls=3, period=1.0)


class LinkedInSource(BaseSource):
    """Fetch company data via LinkedIn Marketing/Companies API.

    Falls back to synthetic mock data when LINKEDIN_ACCESS_TOKEN is absent.
    """

    source_type = "social"
    source_detail = "LinkedIn API"

    def __init__(self) -> None:
        self._token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")

    @retry(max_attempts=3, initial_delay=2.0)
    def _search_companies(self, query: str) -> list[dict]:
        _LI_RATE_LIMITER.acquire()
        data = _get(
            "https://api.linkedin.com/v2/organizations",
            params={
                "q": "search",
                "query.keywords": query,
                "projection": "(elements*(id,localizedName,localizedWebsite,primaryOrganizationType))",
                "count": 10,
            },
            headers={"Authorization": "Bearer " + self._token},
        )
        return data.get("elements", [])

    def fetch(self, voivodeship: str, industries: list[str]) -> list[CompanyProfile]:
        if not self._token:
            logger.debug("LinkedInSource: no token, using mock fallback")
            return _generate_profiles(voivodeship, industries, self.source_type, self.source_detail, count_per_industry=3)

        profiles: list[CompanyProfile] = []
        for industry in industries:
            try:
                companies = self._search_companies(f"{industry} Poland {voivodeship}")
                for company in companies[:5]:
                    profiles.append(
                        CompanyProfile(
                            company_name=company.get("localizedName", ""),
                            industry=industry,
                            voivodeship=voivodeship,
                            website=company.get("localizedWebsite", ""),
                            source_type=self.source_type,
                            source_detail=self.source_detail,
                            acquired_at=datetime.now(timezone.utc),
                        )
                    )
            except Exception as exc:
                logger.warning("LinkedInSource fetch error for %s/%s: %s — using mock fallback", voivodeship, industry, exc)
                profiles.extend(
                    _generate_profiles(voivodeship, [industry], self.source_type, self.source_detail, count_per_industry=3)
                )
        return profiles


# ---------------------------------------------------------------------------
# Google Maps / Places API
# ---------------------------------------------------------------------------

_GMAPS_RATE_LIMITER = RateLimiter(max_calls=10, period=1.0)


class GoogleMapsSource(BaseSource):
    """Fetch local businesses via Google Places Text Search API.

    Falls back to synthetic mock data when GOOGLE_MAPS_API_KEY is absent.
    """

    source_type = "mapa"
    source_detail = "Google Maps Places API"

    def __init__(self) -> None:
        self._key = os.getenv("GOOGLE_MAPS_API_KEY", "")

    @retry(max_attempts=3, initial_delay=1.0)
    def _text_search(self, query: str) -> list[dict]:
        _GMAPS_RATE_LIMITER.acquire()
        data = _get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={
                "query": query,
                "language": "pl",
                "key": self._key,
            },
        )
        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            raise RuntimeError(f"Places API status: {data.get('status')}")
        return data.get("results", [])

    def fetch(self, voivodeship: str, industries: list[str]) -> list[CompanyProfile]:
        if not self._key:
            logger.debug("GoogleMapsSource: no API key, using mock fallback")
            return _generate_profiles(voivodeship, industries, self.source_type, self.source_detail, count_per_industry=7)

        profiles: list[CompanyProfile] = []
        for industry in industries:
            try:
                places = self._text_search(f"{industry} {voivodeship} Polska")
                for place in places[:7]:
                    address = place.get("formatted_address", "")
                    profiles.append(
                        CompanyProfile(
                            company_name=place.get("name", ""),
                            industry=industry,
                            voivodeship=voivodeship,
                            city=address.split(",")[0].strip() if address else "",
                            source_type=self.source_type,
                            source_detail=self.source_detail,
                            acquired_at=datetime.now(timezone.utc),
                        )
                    )
            except Exception as exc:
                logger.warning("GoogleMapsSource fetch error for %s/%s: %s — using mock fallback", voivodeship, industry, exc)
                profiles.extend(
                    _generate_profiles(voivodeship, [industry], self.source_type, self.source_detail, count_per_industry=7)
                )
        return profiles


# ---------------------------------------------------------------------------
# CEIDG / KRS (Polish Business Registries)
# ---------------------------------------------------------------------------

_CEIDG_RATE_LIMITER = RateLimiter(max_calls=5, period=1.0)


class RegistryAPISource(BaseSource):
    """Fetch companies from the Polish CEIDG open API.

    Falls back to synthetic mock data when CEIDG_API_KEY is absent.

    Official docs: https://dane.biznes.gov.pl/api/ceidg/v2
    """

    source_type = "rejestr"
    source_detail = "CEIDG API"

    def __init__(self) -> None:
        self._key = os.getenv("CEIDG_API_KEY", "")

    @retry(max_attempts=3, initial_delay=1.5)
    def _query_ceidg(self, voivodeship: str, pkd: str) -> list[dict]:
        _CEIDG_RATE_LIMITER.acquire()
        data = _get(
            "https://dane.biznes.gov.pl/api/ceidg/v2/firma",
            params={
                "wojewodztwo": voivodeship,
                "pkdKod": pkd,
                "limit": 10,
                "status": "AKTYWNY",
            },
            headers={"Authorization": "Bearer " + self._key},
        )
        return data.get("firma", [])

    # Simple industry → PKD mapping (most common Polish automotive codes)
    _INDUSTRY_PKD = {
        "mechanik": "45.20",
        "dealer samochodowy": "45.11",
        "wulkanizacja": "45.20",
        "auto-serwis": "45.20",
        "lakiernik": "45.20",
        "blacharstwo": "45.20",
        "auto detailing": "45.20",
        "wypożyczalnia samochodów": "77.11",
        "ubezpieczenia samochodowe": "65.12",
        "skup aut": "45.19",
    }

    def fetch(self, voivodeship: str, industries: list[str]) -> list[CompanyProfile]:
        if not self._key:
            logger.debug("RegistryAPISource: no CEIDG key, using mock fallback")
            return _generate_profiles(voivodeship, industries, self.source_type, self.source_detail, count_per_industry=6)

        profiles: list[CompanyProfile] = []
        for industry in industries:
            pkd = self._INDUSTRY_PKD.get(industry.lower(), "45.20")
            try:
                firms = self._query_ceidg(voivodeship, pkd)
                for firm in firms[:6]:
                    addr = firm.get("adresDzialalnosci") or {}
                    profiles.append(
                        CompanyProfile(
                            company_name=firm.get("nazwa", ""),
                            industry=industry,
                            voivodeship=voivodeship,
                            city=addr.get("miejscowosc", ""),
                            county=addr.get("powiat", ""),
                            email=firm.get("email", ""),
                            phone=firm.get("telefon", ""),
                            website=firm.get("www", ""),
                            source_type=self.source_type,
                            source_detail=self.source_detail,
                            acquired_at=datetime.now(timezone.utc),
                        )
                    )
            except Exception as exc:
                logger.warning("RegistryAPISource fetch error for %s/%s: %s — using mock fallback", voivodeship, industry, exc)
                profiles.extend(
                    _generate_profiles(voivodeship, [industry], self.source_type, self.source_detail, count_per_industry=6)
                )
        return profiles
