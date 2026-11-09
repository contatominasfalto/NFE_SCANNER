import importlib.util
import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.metas_bi import ensure_metas_bi_views
from metas_fixture import api_module, create_fixture


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("preparar_metas_bi_test", ROOT / "scripts" / "preparar_metas_bi.py")
provisioner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provisioner)


class MetasBiTests(unittest.TestCase):
    def test_test_database_cannot_target_production_and_vice_versa(self):
        for environment, database in [("testes", "nfe_scanner"), ("producao", "nfe_scanner_dev")]:
            with self.subTest(environment=environment):
                with self.assertRaises(provisioner.ProvisionError):
                    provisioner.validated_url(environment, f"postgresql://user:pass@host/{database}")

    def test_only_postgresql_with_tls_and_explicit_database_is_accepted(self):
        for value in ["mysql://user:pass@host/nfe_scanner_dev", "postgresql://user:pass@host/outro", "postgresql://user:pass@host/nfe_scanner_dev?sslmode=disable"]:
            with self.assertRaises(provisioner.ProvisionError):
                provisioner.validated_url("testes", value)
        url = provisioner.validated_url("testes", "postgresql://user:pass@host/nfe_scanner_dev")
        self.assertEqual(url.query["sslmode"], "require")
        self.assertEqual(url.drivername, "postgresql+psycopg2")

    def test_application_environment_is_never_used_as_fallback(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host/nfe_scanner"}, clear=True), patch.object(sys.stdin, "isatty", return_value=False), patch.object(provisioner, "create_engine") as engine, patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(provisioner.main([]), 1)
            engine.assert_not_called()

    def test_production_requires_literal_confirmation_before_any_connection(self):
        with patch.object(provisioner, "create_engine") as engine, patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(provisioner.main(["--ambiente", "producao", "--executar"]), 1)
            engine.assert_not_called()

    def test_missing_or_weak_password_is_rejected(self):
        for value in ["", "curta", " " * 20, "a" * 20 + "\x00"]:
            with self.assertRaises(provisioner.ProvisionError):
                provisioner.validate_password(value)

    def test_errors_never_expose_url_password_or_driver_exception(self):
        secret = "senha-exclusiva-nao-exibir-123456"
        url = "postgresql://admin:segredo-da-url@host/nfe_scanner_dev"
        with patch.dict(os.environ, {"NFE_SCANNER_TEST_DATABASE_URL": url}, clear=True), patch.object(sys.stdin, "isatty", return_value=True), patch.object(provisioner.getpass, "getpass", return_value=secret), patch.object(provisioner, "create_engine", side_effect=RuntimeError(url + secret)), patch("sys.stderr", new_callable=io.StringIO) as error, patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(provisioner.main(["--executar"]), 1)
            text = error.getvalue() + output.getvalue()
            self.assertNotIn(secret, text)
            self.assertNotIn("segredo-da-url", text)
            self.assertNotIn("postgresql://", text)

    def test_non_postgresql_startup_is_not_modified(self):
        engine = MagicMock()
        engine.dialect.name = "mysql"
        self.assertFalse(ensure_metas_bi_views(engine))
        engine.begin.assert_not_called()

    def test_existing_role_is_not_replaced(self):
        connection = MagicMock()
        connection.execute.return_value.scalar_one.return_value = "nfe_scanner_dev"
        connection.execute.return_value.scalar.return_value = 1
        with self.assertRaises(provisioner.ProvisionError):
            provisioner.inspect_target(connection, "testes")

    def test_diagnostic_is_admin_only(self):
        app, engine, _sessions = create_fixture()
        try:
            with TestClient(app) as client, patch.object(api_module, "metas_bi_status", return_value={"versao": "metas_bi_v1", "views": []}) as status:
                self.assertEqual(client.get("/metas/bi/status/").status_code, 401)
                for role in ["user", "viewer"]:
                    self.assertEqual(client.get("/metas/bi/status/", headers={"X-Test-User": role}).status_code, 403)
                status.assert_not_called()
                self.assertEqual(client.get("/metas/bi/status/", headers={"X-Test-User": "admin"}).status_code, 200)
                status.assert_called_once()
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
