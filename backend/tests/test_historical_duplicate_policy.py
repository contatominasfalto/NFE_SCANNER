import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class HistoricalDuplicatePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = (ROOT / "backend" / "app" / "models.py").read_text(encoding="utf-8")
        cls.database = (ROOT / "backend" / "app" / "database.py").read_text(encoding="utf-8")
        cls.crud = (ROOT / "backend" / "app" / "crud.py").read_text(encoding="utf-8")

    def test_model_no_longer_declares_global_unique_key(self):
        key_line = next(line for line in self.models.splitlines() if "chave_acesso = Column" in line)
        self.assertNotIn("unique=True", key_line)

    def test_database_creates_conditional_unique_index(self):
        self.assertIn("uq_notas_chave_fora_carga_historica", self.database)
        self.assertIn("2025-12-01 00:00:00", self.database)
        self.assertIn("2026-07-01 00:00:00", self.database)

    def test_normal_flow_explicitly_blocks_existing_key(self):
        self.assertIn("class DuplicateNoteError", self.crud)
        self.assertIn("get_nota_by_chave(db, nota.chave_acesso)", self.crud)
        self.assertIn("models.NotaFiscal.id != nota_id", self.crud)

    def test_lookup_by_key_returns_latest_occurrence(self):
        self.assertIn("models.NotaFiscal.data_cadastro.desc()", self.crud)


if __name__ == "__main__":
    unittest.main()
