import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


PANEL_DIR = Path(__file__).resolve().parents[1] / "panel"


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, _tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(attributes["id"])


class TmePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (PANEL_DIR / "index.html").read_text(encoding="utf-8")
        cls.javascript = (PANEL_DIR / "app.js").read_text(encoding="utf-8")
        cls.styles = (PANEL_DIR / "styles.css").read_text(encoding="utf-8")
        parser = IdCollector()
        parser.feed(cls.html)
        cls.ids = parser.ids

    def test_tme_elements_exist_once(self):
        expected = {
            "openTmeReport",
            "tmeDialog",
            "tmeFilterForm",
            "tmeStartDate",
            "tmeEndDate",
            "tmeChart",
            "tmeRankingBody",
            "exportTmePdf",
            "openTmacReport",
            "tmacDialog",
            "tmacFilterForm",
            "tmacChart",
            "tmacDetailChart",
            "tmacRankingBody",
            "tmacAllBody",
            "exportTmacPdf",
        }
        self.assertTrue(expected.issubset(set(self.ids)))
        self.assertEqual(len(self.ids), len(set(self.ids)), "O painel possui IDs HTML duplicados.")

    def test_tme_menu_is_immediately_after_reports(self):
        reports_position = self.html.index('id="openReports"')
        tme_position = self.html.index('id="openTmeReport"')
        tmac_position = self.html.index('id="openTmacReport"')
        audit_position = self.html.index('id="openAudit"')
        self.assertLess(reports_position, tme_position)
        self.assertLess(tme_position, tmac_position)
        self.assertLess(tmac_position, audit_position)

    def test_frontend_restricts_visibility_to_authorized_users(self):
        self.assertIn(
            'setVisible("openTmeReport",p.tme)',
            self.javascript,
        )
        self.assertIn("currentUser?.permissions?.modules", self.javascript)
        self.assertIn("/relatorios/tme/", self.javascript)

    def test_tme_styles_and_cache_versions_are_present(self):
        self.assertIn(".tme-kpis", self.styles)
        self.assertIn(".tme-chart-wrap", self.styles)
        self.assertRegex(self.html, re.compile(r"styles\.css\?v=20260901-02"))
        self.assertRegex(self.html, re.compile(r"app\.js\?v=20260901-02"))

    def test_tme_modal_can_be_maximized_and_resets_when_closed(self):
        self.assertIn('data-maximize="tmeModalSection"', self.html)
        self.assertIn('aria-label="Maximizar relatório"', self.html)
        self.assertIn('setModalMaximized("tmeModalSection",true)', self.javascript)
        self.assertIn('if(id==="tmeDialog")setModalMaximized("tmeModalSection",false)', self.javascript)
        self.assertIn(".tme-header-actions", self.styles)

    def test_tme_pdf_export_uses_selected_period(self):
        self.assertIn('id="exportTmePdf"', self.html)
        self.assertIn("/relatorios/tme/exportar/", self.javascript)
        self.assertIn('credentials:"include"', self.javascript)

    def test_tmac_module_uses_authorized_users_and_combined_chart(self):
        self.assertIn('setVisible("openTmacReport",p.tmac)', self.javascript)
        self.assertIn("/relatorios/tmac-recebimento/", self.javascript)
        self.assertIn('type:"bar",label:"Notas recebidas"', self.javascript)
        self.assertIn('label:"P90"', self.javascript)
        self.assertIn("tmacDetailChart=new Chart", self.javascript)
        self.assertIn('result.notas||[]', self.javascript)

    def test_user_form_supports_profiles_and_modules(self):
        self.assertIn('id="billingRole"', self.html)
        self.assertIn('name="billingModule"', self.html)
        self.assertNotIn("ROLE_PERMISSIONS", self.javascript)
        self.assertIn("PROFILE_DEFAULT_MODULES", self.javascript)

    def test_user_modal_uses_maximized_organized_layout(self):
        self.assertIn('id="usersModalSection"', self.html)
        self.assertIn('data-maximize="usersModalSection"', self.html)
        self.assertIn('class="users-form"', self.html)
        self.assertIn('class="users-list-heading"', self.html)
        self.assertIn('setModalMaximized("usersModalSection",true)', self.javascript)


if __name__ == "__main__":
    unittest.main()
