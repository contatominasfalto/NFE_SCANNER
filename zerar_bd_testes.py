"""Zera com seguranca os dados do banco de homologacao do NFE Scanner.

Este script NAO aceita producao. Ele preserva esquema/tabelas e as contas
padrao necessarias para continuar acessando o painel. Sem ``--executar``, faz
somente uma simulacao com contagens.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, func, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError


EXPECTED_DATABASE = "nfe_scanner_dev"
DATABASE_VARIABLE = "NFE_SCANNER_TEST_DATABASE_URL"
CONFIRMATION = "ZERAR_BANCO_DE_TESTES"
PRESERVED_USERS = {"adm", "bipe", "viewer_user", "faturista01", "faturista02"}
REQUIRED_TABLES = {"notas_fiscais", "audit_logs", "users"}


class ResetError(RuntimeError):
    """Falha segura durante validacao ou reset da homologacao."""


def get_test_database_url() -> str:
    url = (os.getenv(DATABASE_VARIABLE) or os.getenv("DATABASE_URL") or "").strip()
    if not url:
        raise ResetError(f"defina {DATABASE_VARIABLE} com a URL do banco de testes")
    try:
        parsed = make_url(url)
    except Exception as exc:
        raise ResetError("URL do banco invalida") from exc
    if not parsed.drivername.startswith("postgresql"):
        raise ResetError("somente PostgreSQL e aceito")
    database = (parsed.database or "").strip()
    if database != EXPECTED_DATABASE:
        raise ResetError(
            f"OPERACAO BLOQUEADA: esperado {EXPECTED_DATABASE!r}, URL aponta para {database!r}"
        )
    return url


def reflect_required_tables(connection) -> dict[str, Table]:
    available = set(inspect(connection).get_table_names())
    missing = REQUIRED_TABLES - available
    if missing:
        raise ResetError(f"tabelas obrigatorias ausentes: {', '.join(sorted(missing))}")
    metadata = MetaData()
    return {
        name: Table(name, metadata, autoload_with=connection)
        for name in sorted(REQUIRED_TABLES)
    }


def count_rows(connection, table: Table) -> int:
    return int(connection.execute(select(func.count()).select_from(table)).scalar_one())


def collect_counts(connection, tables: dict[str, Table]) -> dict[str, int]:
    users = tables["users"]
    custom_users = connection.execute(
        select(func.count())
        .select_from(users)
        .where(func.lower(users.c.username).not_in(PRESERVED_USERS))
    ).scalar_one()
    return {
        "notas_fiscais": count_rows(connection, tables["notas_fiscais"]),
        "audit_logs": count_rows(connection, tables["audit_logs"]),
        "usuarios_personalizados": int(custom_users),
        "usuarios_preservados": count_rows(connection, users) - int(custom_users),
    }


def write_manifest(before: dict[str, int], after: dict[str, int]) -> Path:
    directory = Path("logs_importacao")
    directory.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = directory / f"reset_testes_{timestamp}.json"
    path.write_text(
        json.dumps(
            {
                "executado_em": datetime.now().isoformat(timespec="seconds"),
                "ambiente": "testes",
                "banco": EXPECTED_DATABASE,
                "antes": before,
                "depois": after,
                "usuarios_preservados": sorted(PRESERVED_USERS),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def run(execute: bool, confirmation: str) -> int:
    if execute and confirmation != CONFIRMATION:
        raise ResetError(f"para executar, informe --confirmar {CONFIRMATION}")

    url = get_test_database_url()
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            tables = reflect_required_tables(connection)
            before = collect_counts(connection, tables)
            print(f"Ambiente confirmado: HOMOLOGACAO")
            print(f"Banco confirmado: {EXPECTED_DATABASE}")
            print(f"Notas a remover: {before['notas_fiscais']}")
            print(f"Eventos de auditoria a remover: {before['audit_logs']}")
            print(f"Usuarios personalizados a remover: {before['usuarios_personalizados']}")
            print(f"Usuarios padrao a preservar: {before['usuarios_preservados']}")

            if not execute:
                print("SIMULACAO concluida: nenhuma alteracao foi gravada.")
                return 0

            # A ordem evita deixar rastros parciais se alguma operacao falhar.
            connection.execute(tables["audit_logs"].delete())
            connection.execute(tables["notas_fiscais"].delete())
            connection.execute(
                tables["users"]
                .delete()
                .where(func.lower(tables["users"].c.username).not_in(PRESERVED_USERS))
            )
            after = collect_counts(connection, tables)

        manifest = write_manifest(before, after)
        print("SUCESSO: banco de testes zerado em uma unica transacao.")
        print(f"Notas restantes: {after['notas_fiscais']}")
        print(f"Eventos de auditoria restantes: {after['audit_logs']}")
        print(f"Usuarios personalizados restantes: {after['usuarios_personalizados']}")
        print(f"Manifesto local: {manifest.resolve()}")
        return 0
    except SQLAlchemyError as exc:
        raise ResetError("falha de banco; toda a transacao foi revertida") from exc
    finally:
        engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Zera somente os dados operacionais do banco nfe_scanner_dev."
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="confirma a gravacao; sem esta opcao ocorre apenas simulacao",
    )
    parser.add_argument("--confirmar", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return run(args.executar, args.confirmar)
    except ResetError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
