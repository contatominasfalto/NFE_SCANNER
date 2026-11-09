import json
import unittest
from calendar import monthrange
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from metas_fixture import access, create_fixture, model_module, models, service


def payload(year=2026, month=11, **values):
    return {"ano": year, "mes": month, "dias": [
        {"data": date(year, month, day).isoformat(), **values}
        for day in range(1, monthrange(year, month)[1] + 1)
    ]}


class MetasTests(unittest.TestCase):
    def setUp(self):
        self.app, self.engine, self.sessions = create_fixture()
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.admin = {"X-Test-User": "admin"}
        self.base = "/metas/expedicao/"
        self.month = self.base + "2026/11/"

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def create(self, data=None, base=None):
        return self.client.post(base or self.base, json=data or payload(), headers=self.admin)

    def audit_logs(self):
        with self.sessions() as db:
            return db.query(models.AuditLog).order_by(models.AuditLog.id).all()

    def test_create_load_edit_and_delete_are_audited(self):
        response = self.create(payload(meta_a1br="1.125", meta_a2br="2.250"))
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(len(result["dias"]), 30)
        self.assertEqual(Decimal(result["totais"]["meta_geral"]), Decimal("101.250"))
        saved = self.client.get(self.month, headers=self.admin)
        self.assertEqual(saved.json(), result)
        changed = payload(meta_a1br="0", meta_a2br=None)
        changed["versao"] = result["versao"]
        changed["id"] = result["id"]
        edited = self.client.put(self.month, json=changed, headers=self.admin)
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()["versao"], 2)
        self.assertIsNone(edited.json()["dias"][0]["meta_a2br"])
        deleted = self.client.delete(self.month + "?versao=2&id=1", headers=self.admin)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get(self.month, headers=self.admin).status_code, 404)
        logs = self.audit_logs()
        self.assertEqual([log.acao for log in logs], ["Cadastrou metas", "Editou metas", "Excluiu metas"])
        details = json.loads(logs[1].detalhes)
        self.assertEqual(Decimal(details["antes"]["dias"][0]["meta_a1br"]), Decimal("1.125"))
        self.assertEqual(Decimal(details["depois"]["dias"][0]["meta_a1br"]), Decimal("0"))
        with self.sessions() as db:
            self.assertEqual(db.query(model_module.MetaDia).count(), 0)

    def test_receiving_adjustments_are_independent_and_can_be_negative(self):
        data = payload(meta_a1br="10.000", meta_a2br="20.000", ajuste_a1br="-1.500", ajuste_a2br="0.250")
        result = self.create(data, "/metas/recebimento/")
        self.assertEqual(result.status_code, 201, result.text)
        totals = result.json()["totais"]
        self.assertEqual(Decimal(totals["meta_geral"]), Decimal("900"))
        self.assertEqual(Decimal(totals["ajuste_geral"]), Decimal("-37.500"))
        self.assertEqual(self.client.get(self.base + "meses/", headers=self.admin).json(), [])
        self.assertEqual(self.create().status_code, 201)

    def test_duplicate_month_does_not_overwrite(self):
        self.assertEqual(self.create(payload(meta_a1br="12")).status_code, 201)
        self.assertEqual(self.create(payload(meta_a1br="99")).status_code, 409)
        self.assertEqual(Decimal(self.client.get(self.month, headers=self.admin).json()["dias"][0]["meta_a1br"]), Decimal("12"))
        self.assertEqual(len(self.audit_logs()), 1)

    def test_leap_year_and_month_end(self):
        for year, month in [(2024, 2), (2025, 2), (2026, 1), (2026, 4)]:
            with self.subTest(year=year, month=month):
                response = self.create(payload(year, month))
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(len(response.json()["dias"]), monthrange(year, month)[1])

    def test_invalid_calendar_is_rejected(self):
        for mode in ["missing", "duplicate", "outside"]:
            data = payload()
            if mode == "missing": data["dias"].pop()
            elif mode == "duplicate": data["dias"][-1] = data["dias"][0]
            else: data["dias"][-1]["data"] = "2026-12-01"
            with self.subTest(mode=mode):
                self.assertEqual(self.create(data).status_code, 422)

    def test_invalid_quantities_and_negative_targets_are_rejected(self):
        for value in ["-1", "NaN", "Infinity", "1.2345", "1000000000000", "texto"]:
            with self.subTest(value=value):
                data = payload()
                data["dias"][0]["meta_a1br"] = value
                self.assertEqual(self.create(data).status_code, 422)
        self.assertEqual(self.audit_logs(), [])

    def test_shipping_cannot_store_receiving_adjustments(self):
        self.assertEqual(self.create(payload(ajuste_a1br="0")).status_code, 422)

    def test_stale_update_and_delete_cannot_discard_another_edit(self):
        self.create()
        data = {**payload(meta_a1br="10"), "versao": 1, "id": 1}
        self.assertEqual(self.client.put(self.month, json=data, headers=self.admin).status_code, 200)
        self.assertEqual(self.client.put(self.month, json=data, headers=self.admin).status_code, 409)
        self.assertEqual(self.client.delete(self.month + "?versao=1&id=1", headers=self.admin).status_code, 409)
        self.assertEqual(len(self.audit_logs()), 2)

    def test_audit_failure_rolls_back_create_update_and_delete(self):
        with patch.object(service, "audit", side_effect=RuntimeError("auditoria indisponivel")):
            self.assertEqual(self.create().status_code, 500)
        self.assertEqual(self.client.get(self.base + "meses/", headers=self.admin).json(), [])
        self.create(payload(meta_a1br="12"))
        with patch.object(service, "audit", side_effect=RuntimeError("auditoria indisponivel")):
            edited = self.client.put(self.month, json={**payload(meta_a1br="99"), "versao": 1, "id": 1}, headers=self.admin)
            self.assertEqual(edited.status_code, 500)
            self.assertEqual(self.client.delete(self.month + "?versao=1&id=1", headers=self.admin).status_code, 500)
        result = self.client.get(self.month, headers=self.admin).json()
        self.assertEqual(result["versao"], 1)
        self.assertEqual(Decimal(result["dias"][0]["meta_a1br"]), Decimal("12"))
        self.assertEqual(len(self.audit_logs()), 1)

    def test_module_is_admin_only_by_default_and_can_be_assigned(self):
        from types import SimpleNamespace
        for role in ["admin", "user", "viewer"]:
            user = SimpleNamespace(role=role, module_access=None)
            self.assertEqual("metas" in access.effective_modules(user), role == "admin")
            custom = SimpleNamespace(role=role, module_access='["metas"]')
            self.assertTrue(access.has_access(custom, "metas", "view"))
            self.assertEqual(access.has_access(custom, "metas", "operate"), role != "viewer")

    def test_http_authorization_for_profiles_and_missing_module(self):
        self.assertEqual(self.client.get(self.base + "meses/").status_code, 401)
        self.create()
        for role in ["user", "viewer"]:
            forbidden = {"X-Test-User": role, "X-Test-Metas": "false"}
            for method, path, body in [("GET", self.month, None), ("POST", self.base, payload(2026, 12)), ("PUT", self.month, {**payload(), "versao": 1, "id": 1}), ("DELETE", self.month + "?versao=1&id=1", None)]:
                self.assertEqual(self.client.request(method, path, json=body, headers=forbidden).status_code, 403)
        viewer = {"X-Test-User": "viewer"}
        self.assertEqual(self.client.get(self.month, headers=viewer).status_code, 200)
        self.assertEqual(self.client.post(self.base, json=payload(2026, 12), headers=viewer).status_code, 403)
        self.assertEqual(self.client.put(self.month, json={**payload(), "versao": 1, "id": 1}, headers=viewer).status_code, 403)
        self.assertEqual(self.client.delete(self.month + "?versao=1&id=1", headers=viewer).status_code, 403)
        self.assertEqual(self.client.post(self.base, json=payload(2026, 12), headers={"X-Test-User": "user"}).status_code, 201)

    def test_months_are_ordered_and_operation_and_period_are_validated(self):
        for year, month in [(2026, 1), (2027, 1), (2026, 12)]: self.create(payload(year, month))
        months = self.client.get(self.base + "meses/", headers=self.admin).json()
        self.assertEqual([(item["ano"], item["mes"]) for item in months], [(2027, 1), (2026, 12), (2026, 1)])
        for path in ["/metas/invalido/meses/", "/metas/expedicao/1999/1/", "/metas/expedicao/2026/13/"]:
            self.assertEqual(self.client.get(path, headers=self.admin).status_code, 422)
        self.assertEqual(self.client.put(self.month, json={**payload(2026, 12), "versao": 1, "id": 1}, headers=self.admin).status_code, 422)

    def test_schema_is_additive_decimal_and_repeatable(self):
        for _ in range(2):
            model_module.MetaMes.__table__.create(self.engine, checkfirst=True)
            model_module.MetaDia.__table__.create(self.engine, checkfirst=True)
        self.assertEqual(set(inspect(self.engine).get_table_names()), {"metas_meses", "metas_dias", "audit_logs"})
        ddl = str(CreateTable(model_module.MetaDia.__table__).compile(dialect=postgresql.dialect()))
        self.assertIn("NUMERIC(15, 3)", ddl)
        self.assertIn("ON DELETE CASCADE", ddl)
        self.assertNotIn("notas_fiscais", ddl)


if __name__ == "__main__":
    unittest.main()
