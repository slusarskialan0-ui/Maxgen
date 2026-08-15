import time

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL, DB_CONNECT_ARGS

def _build_engine_with_retry():
    kwargs = {
        "connect_args": DB_CONNECT_ARGS,
        "pool_pre_ping": True,
    }
    if DATABASE_URL.startswith("postgres"):
        kwargs.update(
            {
                "pool_recycle": 1800,
                "pool_timeout": 30,
                "pool_size": 8,
                "max_overflow": 16,
                "connect_args": {
                    **DB_CONNECT_ARGS,
                    "connect_timeout": 10,
                    "sslmode": "require",
                },
            }
        )

    retries = 5 if DATABASE_URL.startswith("postgres") else 1
    delay = 1.5
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            _engine = create_engine(DATABASE_URL, **kwargs)
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return _engine
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt == retries:
                break
            time.sleep(delay)
            delay = min(delay * 2, 8)
    raise last_exc


engine = _build_engine_with_retry()

# SQLite performance optimisations: WAL mode + page cache + busy timeout
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-32000")   # ~32 MB page cache
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

_SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def SessionLocal():
    retries = 4 if DATABASE_URL.startswith("postgres") else 1
    delay = 0.6
    last_exc = None
    for attempt in range(1, retries + 1):
        db = _SessionFactory()
        try:
            db.execute(text("SELECT 1"))
            return db
        except OperationalError as exc:
            last_exc = exc
            db.close()
            if attempt == retries:
                break
            time.sleep(delay)
            delay = min(delay * 2, 3)
    raise last_exc


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
