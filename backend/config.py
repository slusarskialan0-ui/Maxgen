"""Backend configuration — reads from environment variables and .env files."""
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, unquote, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


def normalize_database_url(database_url: str) -> str:
    db_url = (database_url or "").strip().replace("&amp;", "&")
    if db_url.startswith("sqlite"):
        return db_url
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]
    parts = urlsplit(db_url)
    if parts.scheme:
        normalized_path = quote(unquote(parts.path).rstrip(" "), safe="/")
        normalized_query = parts.query
        if parts.scheme == "postgresql":
            query_params = parse_qsl(parts.query, keep_blank_values=True)
            if not any(key == "sslmode" for key, _ in query_params):
                query_params.append(("sslmode", "require"))
            if not any(key == "channel_binding" for key, _ in query_params):
                query_params.append(("channel_binding", "require"))
            normalized_query = urlencode(query_params)
        db_url = urlunsplit((parts.scheme, parts.netloc, normalized_path, normalized_query, parts.fragment))
    return db_url


def build_db_connect_args(database_url: str) -> dict:
    db_url = normalize_database_url(database_url)
    if db_url.startswith("sqlite"):
        return {"check_same_thread": False}

    return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_HOST: str = "0.0.0.0"
    PORT: int | None = None
    API_PORT: int = 8000
    DATABASE_URL: str = "sqlite:///./polska_leads.db"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    FACEBOOK_ACCESS_TOKEN: str = ""
    LINKEDIN_ACCESS_TOKEN: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    CEIDG_API_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    B2B_LEAD_SCORE_THRESHOLD: int = 65
    PIPELINE_MAX_RETRIES: int = 3
    PIPELINE_SOURCE_TIMEOUT: int = 30


settings = Settings()

API_HOST = settings.API_HOST
API_PORT = settings.PORT or settings.API_PORT
DATABASE_URL = normalize_database_url(settings.DATABASE_URL)
DB_CONNECT_ARGS = build_db_connect_args(DATABASE_URL)

_raw_origins = settings.CORS_ORIGINS
CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

APP_VERSION = "3.0.0"
PROJECT_ID_HEADER = "X-Project-Id"

# ---------------------------------------------------------------------------
# External API credentials (set in environment / Railway / .env)
# ---------------------------------------------------------------------------
FACEBOOK_ACCESS_TOKEN = settings.FACEBOOK_ACCESS_TOKEN
LINKEDIN_ACCESS_TOKEN = settings.LINKEDIN_ACCESS_TOKEN
GOOGLE_MAPS_API_KEY = settings.GOOGLE_MAPS_API_KEY
CEIDG_API_KEY = settings.CEIDG_API_KEY

# Telegram bot (can also be stored in DB via SystemConfig for live updates)
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID

# B2B scraper thresholds
B2B_LEAD_SCORE_THRESHOLD = settings.B2B_LEAD_SCORE_THRESHOLD

# Pipeline behaviour
PIPELINE_MAX_RETRIES = settings.PIPELINE_MAX_RETRIES
PIPELINE_SOURCE_TIMEOUT = settings.PIPELINE_SOURCE_TIMEOUT
