import unittest
from types import SimpleNamespace
from pathlib import Path

from app.access_control import effective_modules, has_access, is_protected_user, permission_payload, request_scope
from app.schemas import FaturistaCreate, FaturistaUpdate


def user(role, modules=None, username="teste"):
    return SimpleNamespace(role=role, module_access=modules, username=username)


class AccessControlTests(unittest.TestCase):
    def test_user_contract_accepts_profile_and_module_selection(self):
        created = FaturistaCreate(nome="teste", senha="senha123", role="user", modulos=["notes", "reports"])
        updated = FaturistaUpdate(nome="teste", ativo=True, role="viewer", modulos=["reports"])
        legacy_update = FaturistaUpdate(nome="teste", ativo=False)
        self.assertEqual(created.modulos, ["notes", "reports"])
        self.assertEqual(updated.role, "viewer")
        self.assertIsNone(legacy_update.role)
        self.assertIsNone(legacy_update.modulos)

    def test_existing_profiles_keep_their_defaults(self):
        self.assertEqual(effective_modules(user("user")), {"notes", "reports"})
        self.assertEqual(effective_modules(user("viewer")), {"notes"})
        self.assertIn("users", effective_modules(user("admin")))

    def test_standard_can_operate_only_enabled_modules(self):
        current = user("user", '["notes", "reports", "tme"]')
        self.assertTrue(has_access(current, "notes", "operate"))
        self.assertTrue(has_access(current, "tme", "download"))
        self.assertFalse(has_access(current, "tmac", "view"))
        self.assertFalse(has_access(current, "users", "manage"))

    def test_viewer_can_view_extra_modules_but_cannot_change_or_download(self):
        current = user("viewer", '["notes", "reports", "tme", "audit"]')
        self.assertTrue(has_access(current, "reports", "view"))
        self.assertTrue(has_access(current, "audit", "view"))
        self.assertFalse(has_access(current, "notes", "operate"))
        self.assertFalse(has_access(current, "tme", "download"))

    def test_admin_always_has_every_module(self):
        permissions = permission_payload(user("admin", "[]"))
        self.assertTrue(all(permissions["modules"].values()))
        self.assertTrue(permissions["actions"]["manage"])

    def test_route_scope_distinguishes_view_download_and_manage(self):
        self.assertEqual(request_scope("/relatorios/tme/", "GET"), ("tme", "view"))
        self.assertEqual(request_scope("/relatorios/tme/exportar/", "GET"), ("tme", "download"))
        self.assertEqual(request_scope("/faturistas/", "POST"), ("users", "manage"))
        self.assertEqual(request_scope("/faturistas/", "GET"), ("users", "view"))

    def test_system_accounts_are_protected(self):
        self.assertTrue(is_protected_user("adm"))
        self.assertTrue(is_protected_user(" BIPE "))
        self.assertTrue(is_protected_user("viewer_user"))
        self.assertFalse(is_protected_user("usuario-comum"))

    def test_database_change_is_additive_and_protected_accounts_are_enforced(self):
        app_dir = Path(__file__).resolve().parents[1] / "app"
        database_source = (app_dir / "database.py").read_text(encoding="utf-8")
        main_source = (app_dir / "main.py").read_text(encoding="utf-8")
        self.assertIn("ALTER TABLE users ADD COLUMN module_access TEXT", database_source)
        self.assertNotIn("DROP COLUMN module_access", database_source)
        self.assertIn("O usuario adm e protegido e nao pode ser modificado", main_source)
        self.assertIn("is_protected_user(atual.nome)", main_source)


if __name__ == "__main__":
    unittest.main()
