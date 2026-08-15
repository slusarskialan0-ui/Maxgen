import unittest

from app.pipeline.evaluator import B2BLeadEvaluator


class B2BLeadEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.evaluator = B2BLeadEvaluator()

    def test_extract_contacts(self):
        phone, email = self.evaluator.extract_contacts(
            "Szukam wykonawcy B2B, kontakt: +48 600 700 800, mail: biuro@test-firma.pl"
        )
        self.assertEqual(phone, "+48600700800")
        self.assertEqual(email, "biuro@test-firma.pl")

    def test_positive_keywords_increase_score(self):
        evaluated = self.evaluator.score(
            title="Szukam wykonawcy B2B",
            description="Stała współpraca dla firmy, faktura VAT, budżet 15000 PLN",
            vat_required="TAK",
        )
        self.assertGreaterEqual(evaluated.score, 65)

    def test_negative_keywords_reduce_score(self):
        evaluated = self.evaluator.score(
            title="Szukam tanio",
            description="Osoba prywatna, brak budżetu, umowa o dzieło",
            vat_required="NIE",
        )
        self.assertLessEqual(evaluated.score, 40)


if __name__ == "__main__":
    unittest.main()
