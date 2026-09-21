import unittest
from html.parser import HTMLParser
from pathlib import Path


PANEL_DIR = Path(__file__).resolve().parents[1] / "panel"


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, _tag, attrs):
        element_id = dict(attrs).get("id")
        if element_id:
            self.ids.add(element_id)


class PanelFilterProcessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (PANEL_DIR / "index.html").read_text(encoding="utf-8")
        cls.javascript = (PANEL_DIR / "app.js").read_text(encoding="utf-8")
        cls.styles = (PANEL_DIR / "styles.css").read_text(encoding="utf-8")
        parser = IdCollector()
        parser.feed(cls.html)
        cls.ids = parser.ids

    def test_processing_overlay_is_accessible(self):
        self.assertIn("filterProcessingOverlay", self.ids)
        self.assertIn("filterProcessingTitle", self.ids)
        self.assertIn("filterProcessingMessage", self.ids)
        self.assertIn('aria-live="assertive"', self.html)

    def test_all_date_filters_use_processing_flow(self):
        expected = (
            '$("bipStartDateFilter").onchange=()=>processDateFilters(true)',
            '$("bipEndDateFilter").onchange=()=>processDateFilters(true)',
            '$("issueStartDateFilter").onchange=()=>processDateFilters(false)',
            '$("issueEndDateFilter").onchange=()=>processDateFilters(false)',
        )
        for listener in expected:
            self.assertIn(listener, self.javascript)

    def test_overlay_blocks_interaction_and_always_closes(self):
        self.assertIn('toggleAttribute("inert",active)', self.javascript)
        self.assertIn("finally{setFilterProcessing(false)}", self.javascript)
        self.assertIn("if(!filterProcessing)loadAll(true)", self.javascript)
        self.assertIn(".filter-processing-overlay", self.styles)
        self.assertIn("z-index:20000", self.styles)


if __name__ == "__main__":
    unittest.main()
