from __future__ import annotations

"""Backend configuration — reads from environment variables for production deploy."""

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))

DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or "sqlite:///./polska_leads.db"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
DB_CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

APP_VERSION = "3.0.0"
PROJECT_ID_HEADER = "X-Project-Id"

FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
CEIDG_API_KEY = os.getenv("CEIDG_API_KEY", "")

PIPELINE_MAX_RETRIES = int(os.getenv("PIPELINE_MAX_RETRIES", "3"))
PIPELINE_SOURCE_TIMEOUT = int(os.getenv("PIPELINE_SOURCE_TIMEOUT", "30"))

CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3"))
CIRCUIT_BREAKER_RECOVERY_SECONDS = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_SECONDS", str(15 * 60)))

B2B_SCRAPER_URLS = [u.strip() for u in os.getenv("B2B_SCRAPER_URLS", "").split(",") if u.strip()]
B2B_SCRAPER_TIMEOUT = int(os.getenv("B2B_SCRAPER_TIMEOUT", "25"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
