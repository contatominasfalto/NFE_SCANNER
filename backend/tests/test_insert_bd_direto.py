import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from insert_bd_direto import ImportValidationError, get_database_url, prepare_file


VALID_ROW = {
    "CHAVE NF": "31251233592510044798550020002476031657683836",
    "DATA/HORA DO BIP": "2025-12-08 17:28:49",
    "DATA EMISSÃO": "2025-12-08 17:28:49",
    "FORNECEDOR": "Vale S.A.",
    "NF": 247603,
    "LOCAL": "PRU",
    "PRODUTO": "AREIA 1 DE BRUCUTU",
    "QUANTIDADE": 34640,
    "VALOR TOTAL": 0,
    "TRANSPORTADOR": "NÃO PREENCHIDO",
    "USUÁRIO": "adm",
    "CNPJ": "NÃO PREENCHIDO",
    "OBSERVAÇÃO": "NÃO PREENCHIDO",
}


class DirectImportTests(unittest.TestCase):
    def write_json(self, payload):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "base_json.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_maps_expected_json_fields_and_dates(self):
        prepared = prepare_file(self.write_json([VALID_ROW]))
        self.assertEqual(len(prepared.rows), 1)
        row = prepared.rows[0]
        self.assertEqual(row["chave_acesso"], VALID_ROW["CHAVE NF"])
        self.assertEqual(row["numero_nf"], "247603")
        self.assertEqual(row["faturista"], "adm")
        self.assertEqual(row["data_cadastro"].hour, 17)
        self.assertFalse(row["erro_salvamento"])

    def test_ignores_repeated_key_inside_same_file(self):
        prepared = prepare_file(self.write_json([VALID_ROW, VALID_ROW]))
        self.assertEqual(len(prepared.rows), 1)
        self.assertEqual(prepared.repeated_in_file, [VALID_ROW["CHAVE NF"]])

    def test_rejects_invalid_key_without_database_access(self):
        invalid = {**VALID_ROW, "CHAVE NF": "123"}
        with self.assertRaises(ImportValidationError):
            prepare_file(self.write_json([invalid]))

    def test_rejects_emission_after_bip(self):
        invalid = {**VALID_ROW, "DATA EMISSÃO": "2025-12-08 18:00:00"}
        with self.assertRaises(ImportValidationError):
            prepare_file(self.write_json([invalid]))

    def test_rejects_negative_quantity(self):
        invalid = {**VALID_ROW, "QUANTIDADE": -1}
        with self.assertRaises(ImportValidationError):
            prepare_file(self.write_json([invalid]))

    def test_environment_rejects_wrong_database(self):
        with patch.dict(
            os.environ,
            {"NFE_SCANNER_TEST_DATABASE_URL": "postgresql://user:pass@host/nfe_scanner"},
            clear=True,
        ):
            with self.assertRaises(ImportValidationError):
                get_database_url("testes")

    def test_environment_accepts_matching_database(self):
        expected = "postgresql://user:pass@host/nfe_scanner_dev"
        with patch.dict(os.environ, {"NFE_SCANNER_TEST_DATABASE_URL": expected}, clear=True):
            self.assertEqual(get_database_url("testes"), expected)


if __name__ == "__main__":
    unittest.main()
