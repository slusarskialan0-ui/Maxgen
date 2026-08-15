import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect  # noqa: E402
from database import engine, Base  # noqa: E402
from app.models import models  # noqa: F401,E402


def test_required_tables_exist():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    required = {"leads", "users", "campaigns", "offers", "payments", "logs", "automations"}
    assert required.issubset(tables)
