import unittest

from app.sources.b2b_sources import CurlCffiB2BSource


class B2BSourcesTests(unittest.TestCase):
    def test_parse_ld_json_and_window_state(self):
        html = """
        <html><head>
          <script type=\"application/ld+json\">{
            \"@type\":\"JobPosting\",
            \"id\":\"abc-1\",
            \"title\":\"Projekt B2B dla agencji\",
            \"description\":\"Stała współpraca, faktura VAT, budżet 12000 PLN. Kontakt: 600700800\",
            \"url\":\"https://example.com/oferta/abc-1\",
            \"budget\":\"12000\",
            \"jobLocation\": {\"city\": \"Warszawa\"}
          }</script>
          <script>window.__PRERENDERED_STATE__ = {"offers":[{"id":"abc-2","name":"Drugie zlecenie","description":"B2B, budżet 8000, kontakt email: lead@firma.pl","url":"https://example.com/oferta/abc-2"}]};</script>
        </head><body></body></html>
        """

        source = CurlCffiB2BSource("test", ["https://example.com"])
        leads = source.parse_html(html, base_url="https://example.com")

        self.assertEqual(len(leads), 2)
        top = max(leads, key=lambda x: x.lead_score)
        self.assertTrue(top.direct_link.startswith("https://example.com/oferta/"))
        self.assertTrue(top.title)


if __name__ == "__main__":
    unittest.main()
