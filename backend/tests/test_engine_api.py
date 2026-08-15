import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from main import app, init_db

init_db()
client = TestClient(app)


def test_engine_generate_and_dashboards():
    res = client.post(
        "/engine/generate",
        json={
            "campaign_name": "Test Offline",
            "industry": "detailing",
            "voivodeship": "mazowieckie",
            "leads_count": 5,
            "budget": 1500,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["generated_leads"] == 5

    conv = client.get("/engine/conversion-dashboard")
    assert conv.status_code == 200
    assert conv.json()["total_leads"] >= 5

    traffic = client.get("/engine/traffic-dashboard")
    assert traffic.status_code == 200
    assert "sources" in traffic.json()


def test_offer_and_payment_flow():
    leads = client.get("/leads", params={"limit": 1})
    assert leads.status_code == 200
    items = leads.json().get("items", [])
    assert items
    lead_id = items[0]["id"]

    offer = client.post("/offers", json={"lead_id": lead_id})
    assert offer.status_code == 201
    offer_data = offer.json()
    assert offer_data["lead_id"] == lead_id

    payment = client.post("/payments/simulate", json={"lead_id": lead_id, "amount": offer_data["amount"], "offer_id": offer_data["id"]})
    assert payment.status_code == 201
    payment_data = payment.json()
    assert payment_data["status"] == "confirmed"


def test_sync_full_export_and_auto_clean():
    export_res = client.get("/sync/export/full/json")
    assert export_res.status_code == 200
    assert "leads" in export_res.text

    clean_res = client.post("/sync/auto-clean", params={"days": 1})
    assert clean_res.status_code == 200
    assert clean_res.json()["ok"] is True
