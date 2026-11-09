"""Aplicação de teste isolada: não importa app.main, config ou .env.

SQLite em memória é usado apenas nesta fixture; o bloqueio do backend real
continua intacto. O ORM e as rotas de metas são os mesmos usados em produção.
"""

import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from fastapi import FastAPI, HTTPException, Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool


PACKAGE = "_metas_isolated_app"
if PACKAGE not in sys.modules:
    package = ModuleType(PACKAGE)
    package.__path__ = [str(Path(__file__).resolve().parents[1] / "app")]
    sys.modules[PACKAGE] = package
    database = ModuleType(f"{PACKAGE}.database")
    database.Base = declarative_base()

    def get_db():
        raise AssertionError("A fixture deve substituir esta dependência.")

    database.get_db = get_db
    sys.modules[database.__name__] = database

database = sys.modules[f"{PACKAGE}.database"]
api_module = importlib.import_module(f"{PACKAGE}.metas_api")
model_module = importlib.import_module(f"{PACKAGE}.metas_models")
models = importlib.import_module(f"{PACKAGE}.models")
service = importlib.import_module(f"{PACKAGE}.metas_service")
access = importlib.import_module(f"{PACKAGE}.access_control")


def create_fixture():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    database.Base.metadata.create_all(engine, tables=[model_module.MetaMes.__table__, model_module.MetaDia.__table__, models.AuditLog.__table__])
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    app = FastAPI()

    def authenticated(request: Request):
        role = request.headers.get("X-Test-User")
        if role not in {"admin", "user", "viewer"}:
            raise HTTPException(401, "Autenticação exigida.")
        enabled = request.headers.get("X-Test-Metas", "true") == "true"
        return SimpleNamespace(username=f"teste_{role}", role=role, module_access='["metas"]' if enabled else '[]')

    def isolated_db():
        with sessions() as db:
            yield db

    app.include_router(api_module.create_metas_router(authenticated))
    app.dependency_overrides[database.get_db] = isolated_db
    return app, engine, sessions
