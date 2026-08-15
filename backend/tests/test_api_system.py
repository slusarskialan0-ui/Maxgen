import os
import sys
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import inspect

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import main  # noqa: E402
from database import engine  # noqa: E402


class ApiSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main.init_db()
        cls.client = TestClient(main.app)

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("status"), "ok")

    def test_required_tables_exist(self):
        tables = set(inspect(engine).get_table_names())
        required = {"leads", "users", "campaigns", "offers", "payments", "automations", "audit_logs"}
        self.assertTrue(required.issubset(tables))

    def test_offers_and_payments_flow(self):
        lead = self.client.post("/leads", json={"full_name": "Test Lead", "email": "test.lead@example.com", "source": "forms_offline"})
        self.assertEqual(lead.status_code, 201)
        lead_id = lead.json()["id"]

        offer = self.client.post("/offers", json={"title": "Oferta testowa", "amount": 1999.99, "lead_id": lead_id, "status": "sent"})
        self.assertEqual(offer.status_code, 201)
        offer_id = offer.json()["id"]

        payment = self.client.post("/payments", json={"amount": 1999.99, "offer_id": offer_id, "status": "pending"})
        self.assertEqual(payment.status_code, 201)
        payment_id = payment.json()["id"]

        sim = self.client.post(f"/payments/{payment_id}/simulate")
        self.assertEqual(sim.status_code, 200)
        self.assertIn(sim.json()["status"], {"pending", "confirmed", "failed"})

        logs = self.client.get(f"/payments/{payment_id}/logs")
        self.assertEqual(logs.status_code, 200)
        self.assertGreaterEqual(len(logs.json()), 1)

    def test_offline_generation_and_automation(self):
        generated = self.client.post(
            "/leads/generate-offline",
            json={
                "traffic": 40,
                "campaign_name": "Offline Test Campaign",
                "industry": "detailing",
                "voivodeship": "mazowieckie",
            },
        )
        self.assertEqual(generated.status_code, 200)
        self.assertGreater(generated.json()["generated_leads"], 0)

        autos = self.client.get("/automations")
        self.assertEqual(autos.status_code, 200)
        names = {a["name"] for a in autos.json()}
        self.assertIn("Auto-predykcja konwersji", names)

    def test_sync_auto_endpoints(self):
        self.assertEqual(self.client.post("/sync/auto-backup").status_code, 200)
        status = self.client.get("/sync/auto-status")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["auto_clean"], "enabled")
        self.assertEqual(self.client.post("/sync/auto-clean", params={"keep_latest": 3}).status_code, 200)


if __name__ == "__main__":
    unittest.main()
