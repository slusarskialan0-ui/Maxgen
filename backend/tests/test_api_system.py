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
        required = {"leads", "users", "campaigns", "offers", "payments", "automations", "audit_logs", "integration_jobs"}
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

    def test_system_readiness_and_ops_status(self):
        ready = self.client.get("/system/readiness")
        self.assertEqual(ready.status_code, 200)
        self.assertIn(ready.json().get("status"), {"ready", "degraded"})
        self.assertIn("checks", ready.json())
        startup = self.client.get("/system/startup-status")
        self.assertEqual(startup.status_code, 200)
        self.assertIn("one_click_ready", startup.json())
        self.assertIn("integration_queue", startup.json())

        liveness = self.client.get("/system/liveness")
        self.assertEqual(liveness.status_code, 200)
        self.assertEqual(liveness.json().get("status"), "ok")

        ops = self.client.get("/system/ops-status")
        self.assertEqual(ops.status_code, 200)
        self.assertIn("backups", ops.json())
        self.assertIn("alerts", ops.json())
        self.assertIn("integration_queue", ops.json())

    def test_automation_full_cycle_and_monetization(self):
        lead = self.client.post(
            "/leads",
            json={
                "full_name": "Cycle Lead",
                "email": "cycle.lead@example.com",
                "company": "Cycle Cars",
                "industry": "detailing",
                "voivodeship": "mazowieckie",
                "notes": "Lead gotowy do pełnej automatyzacji follow-up i oferty premium.",
            },
        )
        self.assertEqual(lead.status_code, 201)
        run = self.client.post("/automations/run-full-cycle")
        self.assertEqual(run.status_code, 200)
        self.assertTrue(run.json()["ok"])
        self.assertGreaterEqual(run.json()["processed"], 1)

        preview = self.client.get("/biznes/plan-upgrade-preview")
        self.assertEqual(preview.status_code, 200)
        self.assertIn("active_plan", preview.json())
        self.assertIn("usage", preview.json())

        segments = self.client.get("/biznes/segments")
        self.assertEqual(segments.status_code, 200)
        self.assertIn("by_industry", segments.json())
        self.assertIn("by_voivodeship", segments.json())

    def test_connectors_queue_retry_flow(self):
        connectors = self.client.get("/sync/connectors")
        self.assertEqual(connectors.status_code, 200)
        self.assertIn("connectors", connectors.json())

        bad = self.client.post("/sync/connectors/webhook/enqueue", json={"url": "notaurl"})
        self.assertEqual(bad.status_code, 200)
        run_1 = self.client.post("/sync/connectors/run-pending", params={"limit": 10})
        self.assertEqual(run_1.status_code, 200)
        self.assertGreaterEqual(run_1.json()["processed"], 1)

        jobs = self.client.get("/sync/connectors/jobs", params={"limit": 20})
        self.assertEqual(jobs.status_code, 200)
        self.assertGreaterEqual(len(jobs.json()), 1)


if __name__ == "__main__":
    unittest.main()
