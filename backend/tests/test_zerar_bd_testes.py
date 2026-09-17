import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from zerar_bd_testes import EXPECTED_DATABASE, ResetError, get_test_database_url


class ResetTestDatabaseTests(unittest.TestCase):
    def test_accepts_only_test_database(self):
        expected = f"postgresql://user:pass@host/{EXPECTED_DATABASE}"
        with patch.dict(os.environ, {"NFE_SCANNER_TEST_DATABASE_URL": expected}, clear=True):
            self.assertEqual(get_test_database_url(), expected)

    def test_blocks_production_database(self):
        production = "postgresql://user:pass@host/nfe_scanner"
        with patch.dict(os.environ, {"NFE_SCANNER_TEST_DATABASE_URL": production}, clear=True):
            with self.assertRaises(ResetError):
                get_test_database_url()

    def test_blocks_missing_database_url(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ResetError):
                get_test_database_url()


if __name__ == "__main__":
    unittest.main()
