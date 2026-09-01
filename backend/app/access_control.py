from __future__ import annotations

import json


PROFILE_ADMIN = "admin"
PROFILE_STANDARD = "user"
PROFILE_VIEWER = "viewer"
VALID_PROFILES = {PROFILE_ADMIN, PROFILE_STANDARD, PROFILE_VIEWER}
MODULES = ("notes", "reports", "tme", "tmac", "users", "audit", "swagger")
PROFILE_LABELS = {PROFILE_ADMIN: "Admin", PROFILE_STANDARD: "Standard", PROFILE_VIEWER: "Viewer"}
DEFAULT_MODULES = {
    PROFILE_ADMIN: set(MODULES),
    PROFILE_STANDARD: {"notes", "reports"},
    PROFILE_VIEWER: {"notes"},
}
PROTECTED_USERS = {"adm", "bipe", "viewer_user"}


def normalize_profile(role: str | None) -> str:
    value = (role or PROFILE_STANDARD).strip().casefold()
    return value if value in VALID_PROFILES else PROFILE_STANDARD


def parse_modules(raw: str | list[str] | None, role: str) -> set[str]:
    if raw is None or raw == "":
        return set(DEFAULT_MODULES[normalize_profile(role)])
    try:
        values = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        values = []
    return {str(value) for value in values if str(value) in MODULES}


def serialize_modules(values: list[str] | set[str]) -> str:
    return json.dumps(sorted({value for value in values if value in MODULES}), ensure_ascii=False)


def is_protected_user(username: str | None) -> bool:
    return (username or "").strip().casefold() in PROTECTED_USERS


def effective_modules(user) -> set[str]:
    role = normalize_profile(getattr(user, "role", None))
    if role == PROFILE_ADMIN:
        return set(MODULES)
    return parse_modules(getattr(user, "module_access", None), role)


def profile_allows(user, action: str) -> bool:
    role = normalize_profile(getattr(user, "role", None))
    if role == PROFILE_ADMIN:
        return True
    if role == PROFILE_STANDARD:
        return action in {"view", "operate", "download"}
    return action == "view"


def has_access(user, module: str, action: str = "view") -> bool:
    return module in effective_modules(user) and profile_allows(user, action)


def request_scope(path: str, method: str) -> tuple[str, str] | None:
    action = "view" if method.upper() == "GET" else "operate"
    if path.startswith("/relatorios/tmac-recebimento"):
        return "tmac", "download" if "/exportar/" in path else action
    if path.startswith("/relatorios/tme"):
        return "tme", "download" if "/exportar/" in path else action
    if path.startswith("/relatorios/"):
        return "reports", "download" if "/exportar/" in path else action
    if path.startswith("/faturistas/"):
        return "users", "view" if method.upper() == "GET" else "manage"
    if path.startswith("/auditoria/"):
        return "audit", "view"
    if path.startswith("/barcode-nf/") or path.startswith("/notas/"):
        return "notes", action
    if path == "/relatorio/":
        return "notes", "download"
    return None


def permission_payload(user) -> dict:
    modules = effective_modules(user)
    role = normalize_profile(getattr(user, "role", None))
    return {
        "modules": {module: module in modules for module in MODULES},
        "actions": {
            "view": True,
            "operate": role in {PROFILE_ADMIN, PROFILE_STANDARD},
            "download": role in {PROFILE_ADMIN, PROFILE_STANDARD},
            "manage": role == PROFILE_ADMIN,
        },
    }
