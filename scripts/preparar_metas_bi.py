"""Provisiona um login PostgreSQL novo, somente para as tres views de Metas.

Nao importa o backend ou .env. Simulacao por padrao. A senha e solicitada
privadamente apenas na gravacao; nenhuma credencial e impressa ou salva.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.metas_bi import VIEW_NAMES, apply_metas_bi_views


ENVIRONMENTS = {
    "testes": ("NFE_SCANNER_TEST_DATABASE_URL", "nfe_scanner_dev", "powerbi_metas_testes"),
    "producao": ("NFE_SCANNER_PROD_DATABASE_URL", "nfe_scanner", "powerbi_metas"),
}
PRODUCTION_CONFIRMATION = "PREPARAR_BI_EM_PRODUCAO"


class ProvisionError(ValueError):
    pass


def validated_url(environment, value):
    try:
        url = make_url(value)
    except Exception:
        raise ProvisionError("URL PostgreSQL invalida.") from None
    expected = ENVIRONMENTS[environment][1]
    if url.get_backend_name() != "postgresql" or url.database != expected:
        raise ProvisionError(f"Operacao bloqueada: o ambiente {environment} exige PostgreSQL no banco {expected}.")
    if url.query.get("sslmode", "require") not in {"require", "verify-ca", "verify-full"}:
        raise ProvisionError("Use conexao criptografada com sslmode=require ou validacao mais forte.")
    return url.set(drivername="postgresql+psycopg2", query={**url.query, "sslmode": url.query.get("sslmode", "require")})


def validate_password(password):
    if len(password) < 20 or not password.strip() or "\x00" in password:
        raise ProvisionError("A senha exclusiva do BI deve ter pelo menos 20 caracteres e nao conter byte nulo.")


def inspect_target(connection, environment):
    _, expected_database, username = ENVIRONMENTS[environment]
    if connection.execute(text("SELECT current_database()")).scalar_one() != expected_database:
        raise ProvisionError("O servidor confirmou um banco diferente do ambiente solicitado.")
    if connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": username}).scalar():
        raise ProvisionError(f"O usuario {username} ja existe. Nenhuma senha ou permissao existente sera alterada.")
    for name in ("metas_meses", "metas_dias"):
        if not connection.execute(text("SELECT to_regclass(:name)"), {"name": f"public.{name}"}).scalar():
            raise ProvisionError("As tabelas de Metas ainda nao foram publicadas neste ambiente.")


def provision(connection, environment, password):
    validate_password(password)
    inspect_target(connection, environment)
    _, database, username = ENVIRONMENTS[environment]
    # Identificadores vem exclusivamente das constantes acima, com quoting do driver.
    quote = connection.dialect.identifier_preparer.quote
    role = quote(username)
    apply_metas_bi_views(connection)
    connection.execute(text(
        f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD :password"
    ), {"password": password})
    connection.execute(text(f"GRANT CONNECT ON DATABASE {quote(database)} TO {role}"))
    connection.execute(text(f"GRANT USAGE ON SCHEMA powerbi TO {role}"))
    connection.execute(text(f"GRANT SELECT ON {', '.join('powerbi.' + name for name in VIEW_NAMES)} TO {role}"))
    connection.execute(text(f"ALTER ROLE {role} SET default_transaction_read_only = on"))
    # Impede uma confirmacao enganosa se o banco ja conceder privilegios amplos a PUBLIC.
    broad_access = connection.execute(text("""
        SELECT 1
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
          AND n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
          AND NOT (n.nspname = 'powerbi' AND c.relname = ANY(:views))
          AND (has_table_privilege(:role, c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
               OR has_any_column_privilege(:role, c.oid, 'SELECT,UPDATE'))
        LIMIT 1
    """), {"role": username, "views": list(VIEW_NAMES)}).scalar()
    if broad_access:
        raise ProvisionError("Ha permissoes herdadas de PUBLIC fora das views de Metas. Provisionamento revertido; revisar permissoes com o administrador.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ambiente", choices=ENVIRONMENTS, default="testes")
    parser.add_argument("--executar", action="store_true")
    parser.add_argument("--confirmar-producao", default="")
    args = parser.parse_args(argv)
    try:
        if args.executar and args.ambiente == "producao" and args.confirmar_producao != PRODUCTION_CONFIRMATION:
            raise ProvisionError(f"Producao exige aprovacao previa e --confirmar-producao {PRODUCTION_CONFIRMATION}.")
        variable, database, username = ENVIRONMENTS[args.ambiente]
        if not sys.stdin.isatty() and (args.executar or not os.getenv(variable)):
            raise ProvisionError("Use um terminal interativo para informar credenciais com entrada oculta.")
        raw_url = os.getenv(variable) or getpass.getpass(f"URL administrativa EXTERNA de {database} (entrada oculta): ")
        url = validated_url(args.ambiente, raw_url)
        password = None
        if args.executar:
            password = getpass.getpass(f"Nova senha exclusiva de {username} (minimo 20 caracteres): ")
            validate_password(password)
            if password != getpass.getpass("Confirme a nova senha: "):
                raise ProvisionError("As senhas nao conferem.")
        engine = create_engine(url, pool_pre_ping=True, hide_parameters=True)
        try:
            with engine.begin() as connection:
                if args.executar:
                    provision(connection, args.ambiente, password)
                else:
                    inspect_target(connection, args.ambiente)
        finally:
            engine.dispose()
        print(f"{'Concluido' if args.executar else 'SIMULACAO, nenhuma gravacao'}: {database}; usuario {username}.")
        print("Escopo: leitura somente de powerbi.vw_metas, vw_metas_expedicao e vw_metas_recebimento.")
        if not args.executar:
            print("Revise o ambiente; para criar o login use --executar. Producao depende de aprovacao.")
        return 0
    except ProvisionError as exc:
        print(f"BLOQUEADO: {exc}", file=sys.stderr)
    except (EOFError, KeyboardInterrupt):
        print("Operacao cancelada; nenhuma credencial foi exibida.", file=sys.stderr)
    except Exception:
        # Nao imprimir excecoes de driver: podem incluir URLs, parametros ou senhas.
        print("Falha de conexao ou provisionamento. Transacao revertida; confira acesso administrativo e permissoes. Nenhuma credencial foi exibida.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
