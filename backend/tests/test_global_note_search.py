import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class GlobalNoteSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        cls.crud = (ROOT / "backend" / "app" / "crud.py").read_text(encoding="utf-8")
        cls.javascript = (ROOT / "backend" / "panel" / "app.js").read_text(encoding="utf-8")

    def test_authenticated_notes_endpoint_accepts_global_search(self):
        self.assertIn("busca: str | None = Query(", self.main)
        self.assertIn("busca=busca", self.main)
        self.assertIn('description="Pesquisa global independente do periodo de bip."', self.main)

    def test_crud_searches_relevant_fields_and_ignores_dates(self):
        self.assertIn('termo = (busca or "").strip()', self.crud)
        for field in (
            "chave_acesso",
            "numero_nf",
            "serie",
            "nome_fornecedor",
            "produto",
            "transportador",
            "cnpj_fornecedor",
            "faturista",
            "lider_operacional",
            "local",
            "observacao",
        ):
            self.assertIn(f"NotaFiscal.{field}.ilike", self.crud)
        for field in ("data_cadastro", "data_emissao", "quantidade", "valor_total"):
            self.assertIn(f"cast(models.NotaFiscal.{field}, String).ilike", self.crud)
        self.assertIn("else:\n        if data_cadastro_inicio:", self.crud)

    def test_frontend_uses_server_search_without_date_parameters(self):
        self.assertIn("busca:query", self.javascript)
        self.assertIn('$("searchInput").oninput=scheduleGlobalSearch', self.javascript)
        self.assertIn("scheduleGlobalSearch(wait=700)", self.javascript)
        self.assertIn("setTimeout(()=>processGlobalSearch(),wait)", self.javascript)
        self.assertIn("if(refreshing){scheduleGlobalSearch(150);return}", self.javascript)
        self.assertIn("!==requestedQuery)scheduleGlobalSearch(0)", self.javascript)
        self.assertNotIn('async function processGlobalSearch(){if(filterProcessing)return', self.javascript)
        self.assertNotIn('message=query?"Pesquisando em todo o banco de dados', self.javascript)
        self.assertIn("if(q){filtered=sortNotesForTable([...notes])", self.javascript)


if __name__ == "__main__":
    unittest.main()
