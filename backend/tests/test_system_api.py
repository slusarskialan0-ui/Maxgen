import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

os.environ.setdefault("DATABASE_URL", "sqlite:///./polska_leads.db")

from main import app  # noqa: E402


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_campaign_lead_offer_payment_flow():
    campaign = client.post("/campaigns", json={"name": "Test Kampania", "source": "offline_ads", "budget": 1200}).json()
    campaign_id = campaign["id"]

    lead = client.post("/leads", json={
        "full_name": "Jan Testowy",
        "email": "jan.testowy@example.com",
        "company": "Auto Test Sp. z o.o.",
        "industry": "Moto",
        "voivodeship": "Mazowieckie",
        "campaign_id": campaign_id,
    }).json()
    lead_id = lead["id"]

    offer_resp = client.post("/offers", json={
        "lead_id": lead_id,
        "campaign_id": campaign_id,
        "title": "Oferta testowa",
        "amount": 1999.0,
    })
    assert offer_resp.status_code == 201
    offer_id = offer_resp.json()["id"]

    payment_resp = client.post("/payments", json={"lead_id": lead_id, "offer_id": offer_id, "amount": 1999.0})
    assert payment_resp.status_code == 201
    payment_id = payment_resp.json()["id"]

    confirm_resp = client.post(f"/payments/{payment_id}/confirm")
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"
    assert confirm_resp.json()["confirmation_code"].startswith("OFF-")


def test_offline_generation_and_automation_endpoints():
    gen = client.post("/leads/generate-offline", json={"count": 8, "project_id": "test-suite"})
    assert gen.status_code == 200
    assert gen.json()["created"] == 8

    autos = client.get("/automations")
    assert autos.status_code == 200
    assert isinstance(autos.json(), list)

    logs = client.get("/payments/logs/recent")
    assert logs.status_code == 200
    assert isinstance(logs.json(), list)
