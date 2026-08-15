"""Backend configuration — reads from environment variables for production deploy."""
import os

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))

# Production deploy: set DATABASE_URL env var (e.g. postgresql://...)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./polska_leads.db")
# SQLite requires check_same_thread=False; Postgres does not support it
DB_CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

APP_VERSION = "3.0.0"
PROJECT_ID_HEADER = "X-Project-Id"

# ---------------------------------------------------------------------------
# External API credentials (set in environment / Fly / .env)
# ---------------------------------------------------------------------------
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
CEIDG_API_KEY = os.getenv("CEIDG_API_KEY", "")

# Pipeline behaviour
PIPELINE_MAX_RETRIES = int(os.getenv("PIPELINE_MAX_RETRIES", "3"))
PIPELINE_SOURCE_TIMEOUT = int(os.getenv("PIPELINE_SOURCE_TIMEOUT", "30"))
