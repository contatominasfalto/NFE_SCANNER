import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, _tag, attrs):
        element_id = dict(attrs).get("id")
        if element_id:
            self.ids.append(element_id)


class ThroughputPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "backend" / "panel" / "index.html").read_text(encoding="utf-8")
        cls.javascript = (ROOT / "backend" / "panel" / "app.js").read_text(encoding="utf-8")
        cls.main = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        parser = IdCollector()
        parser.feed(cls.html)
        cls.ids = parser.ids

    def test_sidebar_order_and_unique_elements(self):
        self.assertLess(self.html.index('id="openTmacReport"'), self.html.index('id="openTphbReport"'))
        self.assertLess(self.html.index('id="openTphbReport"'), self.html.index('id="openTpheReport"'))
        self.assertEqual(len(self.ids), len(set(self.ids)))
        for prefix in ("tphb", "tphe"):
            for suffix in ("Dialog", "Date", "HourlyChart", "MonthChart", "YearChart"):
                self.assertIn(prefix + suffix, self.ids)

    def test_reports_use_distinct_endpoints_and_pdf_exports(self):
        for prefix in ("tphb", "tphe"):
            self.assertIn(f'@app.get("/relatorios/{prefix}/"', self.main)
            self.assertIn(f'@app.get("/relatorios/{prefix}/exportar/"', self.main)
            self.assertIn(f'`/relatorios/${{prefix}}/?data=', self.javascript)
            self.assertIn(f'`/relatorios/${{prefix}}/exportar/?data=', self.javascript)

    def test_three_chart_views_and_report_permission(self):
        self.assertIn('setVisible("openTphbReport",p.tphb)', self.javascript)
        self.assertIn('setVisible("openTpheReport",p.tphe)', self.javascript)
        self.assertIn('name="billingModule" value="tphb"', self.html)
        self.assertIn('name="billingModule" value="tphe"', self.html)
        self.assertIn('user:["notes","reports","tphb","tphe"]', self.javascript)
        self.assertIn('result.horas||[]', self.javascript)
        self.assertIn('result.dias_mes||[]', self.javascript)
        self.assertIn('result.meses_ano||[]', self.javascript)


if __name__ == "__main__":
    unittest.main()
