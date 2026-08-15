import unittest
from fastapi.testclient import TestClient

from app.models.models import Automation, AuditLog, Campaign, Lead, Log, Offer, Payment, User
from database import SessionLocal
from main import app, init_db


class AutoSystemTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls._client_ctx = TestClient(app)
        cls.client = cls._client_ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._client_ctx.__exit__(None, None, None)

    def setUp(self):
        db = SessionLocal()
        try:
            for model in [Payment, Offer, Campaign, Lead, Automation, Log, AuditLog, User]:
                db.query(model).delete()
            db.commit()
        finally:
            db.close()

    def seed(self):
        self.client.post('/auto/bootstrap')
        self.client.post('/auto/leads/generate', json={
            'voivodeship': 'mazowieckie',
            'industries': ['mechanik', 'dealer samochodowy', 'wulkanizacja'],
            'limit': 9,
        })

    def test_offline_generation_and_sales(self):
        self.seed()
        leads_response = self.client.get('/auto/leads')
        self.assertEqual(leads_response.status_code, 200)
        self.assertGreater(leads_response.json()['total'], 0)

        sales_response = self.client.post('/auto/sales/run')
        self.assertEqual(sales_response.status_code, 200)
        self.assertGreaterEqual(sales_response.json()['processed'], 1)

        offers_response = self.client.get('/auto/offers')
        self.assertEqual(offers_response.status_code, 200)
        self.assertGreater(offers_response.json()['total'], 0)

    def test_campaigns_payments_and_sync(self):
        self.seed()
        self.client.post('/auto/sales/run')

        campaigns_response = self.client.post('/auto/campaigns/generate')
        self.assertEqual(campaigns_response.status_code, 200)
        self.assertGreaterEqual(campaigns_response.json()['created'], 1)

        payments_response = self.client.post('/auto/payments/simulate')
        self.assertEqual(payments_response.status_code, 200)

        conversion_response = self.client.get('/auto/dashboard/conversion')
        revenue_response = self.client.get('/auto/dashboard/revenue')
        export_response = self.client.post('/auto/sync/export')
        backup_response = self.client.post('/auto/sync/backup')
        recovery_response = self.client.post('/auto/sync/recovery')

        self.assertEqual(conversion_response.status_code, 200)
        self.assertEqual(revenue_response.status_code, 200)
        self.assertEqual(export_response.status_code, 200)
        self.assertIn('leads', export_response.json())
        self.assertEqual(backup_response.status_code, 200)
        self.assertEqual(recovery_response.status_code, 200)

    def test_evolution_mode_report(self):
        response = self.client.post('/evolution/run', json={
            'voivodeship': 'mazowieckie',
            'industries': ['mechanik', 'dealer samochodowy'],
            'limit': 12,
            'keep_latest_backups': 5,
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get('status'), 'ok')
        self.assertIn('report', payload)

        status_response = self.client.get('/evolution/status')
        report_response = self.client.get('/evolution/report')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(report_response.status_code, 200)
        self.assertEqual(report_response.json().get('mode'), 'OVERKILL_EVOLUTION_MODE')


if __name__ == '__main__':
    unittest.main()
