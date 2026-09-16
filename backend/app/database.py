from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL

IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_MYSQL = DATABASE_URL.startswith("mysql")
connect_args = {"check_same_thread": False, "timeout": 30} if IS_SQLITE else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=not IS_SQLITE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def configure_sqlite_connection(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


def ensure_schema():
    inspector = inspect(engine)
    if "notas_fiscais" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("notas_fiscais")}
    bool_default = "0" if IS_SQLITE else "FALSE"
    string_type = "VARCHAR(255)" if IS_MYSQL else "VARCHAR"
    migrations = {
        "local": f"ALTER TABLE notas_fiscais ADD COLUMN local {string_type}",
        "produto": "ALTER TABLE notas_fiscais ADD COLUMN produto TEXT",
        "quantidade": "ALTER TABLE notas_fiscais ADD COLUMN quantidade FLOAT",
        "transportador": f"ALTER TABLE notas_fiscais ADD COLUMN transportador {string_type}",
        "faturista": f"ALTER TABLE notas_fiscais ADD COLUMN faturista {string_type} DEFAULT 'BIPE'",
        "lider_operacional": f"ALTER TABLE notas_fiscais ADD COLUMN lider_operacional {string_type}",
        "erro_salvamento": f"ALTER TABLE notas_fiscais ADD COLUMN erro_salvamento BOOLEAN DEFAULT {bool_default} NOT NULL",
        "erro_detalhe": "ALTER TABLE notas_fiscais ADD COLUMN erro_detalhe TEXT",
    }
    with engine.begin() as connection:
        for column, statement in migrations.items():
            if column not in columns:
                connection.execute(text(statement))
        if "centro_custo" in columns and "local_areia" in columns:
            connection.execute(
                text(
                    "UPDATE notas_fiscais SET local = "
                    "COALESCE(NULLIF(local, ''), NULLIF(centro_custo, ''), NULLIF(local_areia, ''))"
                )
            )
        elif "centro_custo" in columns:
            connection.execute(
                text("UPDATE notas_fiscais SET local = COALESCE(NULLIF(local, ''), NULLIF(centro_custo, ''))")
            )
        elif "local_areia" in columns:
            connection.execute(
                text("UPDATE notas_fiscais SET local = COALESCE(NULLIF(local, ''), NULLIF(local_areia, ''))")
            )
        connection.execute(
            text(
                "UPDATE notas_fiscais SET local = CASE "
                "WHEN local = 'A1BR/PRU' THEN 'PRU' "
                "WHEN local IN ('A1BR', 'A2BR') THEN 'CDMA' "
                "ELSE local END"
            )
        )
        indexes = {index["name"] for index in inspector.get_indexes("notas_fiscais")}
        if "ix_notas_fiscais_centro_custo" in indexes:
            if IS_MYSQL:
                connection.execute(text("DROP INDEX ix_notas_fiscais_centro_custo ON notas_fiscais"))
            else:
                connection.execute(text("DROP INDEX IF EXISTS ix_notas_fiscais_centro_custo"))
        if "centro_custo" in columns:
            connection.execute(text("ALTER TABLE notas_fiscais DROP COLUMN centro_custo"))
        if "local_areia" in columns:
            connection.execute(text("ALTER TABLE notas_fiscais DROP COLUMN local_areia"))
        indexes = {index["name"] for index in inspector.get_indexes("notas_fiscais")}
        if "ix_notas_fiscais_local" not in indexes:
            connection.execute(text("CREATE INDEX ix_notas_fiscais_local ON notas_fiscais (local)"))
        if not IS_MYSQL and not IS_SQLITE:
            # Permite chaves repetidas apenas na carga historica, identificada
            # pela data real do bip. Fora da janela, o PostgreSQL ainda protege
            # contra duas gravacoes simultaneas da mesma chave.
            historical_start = "2025-12-01 00:00:00"
            historical_end = "2026-07-01 00:00:00"
            duplicates_outside_window = connection.execute(
                text(
                    "SELECT COUNT(*) FROM ("
                    "SELECT chave_acesso FROM notas_fiscais "
                    "WHERE chave_acesso IS NOT NULL AND ("
                    "data_cadastro IS NULL OR data_cadastro < :inicio OR data_cadastro >= :fim"
                    ") GROUP BY chave_acesso HAVING COUNT(*) > 1"
                    ") duplicadas"
                ),
                {"inicio": historical_start, "fim": historical_end},
            ).scalar_one()
            if duplicates_outside_window:
                raise RuntimeError(
                    "Existem chaves duplicadas fora da janela historica; "
                    "migracao de unicidade cancelada."
                )

            inspector = inspect(connection)
            quote = connection.dialect.identifier_preparer.quote
            for constraint in inspector.get_unique_constraints("notas_fiscais"):
                if constraint.get("column_names") == ["chave_acesso"] and constraint.get("name"):
                    connection.execute(
                        text(f"ALTER TABLE notas_fiscais DROP CONSTRAINT {quote(constraint['name'])}")
                    )

            inspector = inspect(connection)
            for index in inspector.get_indexes("notas_fiscais"):
                if (
                    index.get("unique")
                    and index.get("column_names") == ["chave_acesso"]
                    and index.get("name")
                    and index.get("name") != "uq_notas_chave_fora_carga_historica"
                ):
                    connection.execute(text(f"DROP INDEX IF EXISTS {quote(index['name'])}"))

            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_notas_fiscais_chave_acesso "
                    "ON notas_fiscais (chave_acesso)"
                )
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_notas_chave_fora_carga_historica "
                    "ON notas_fiscais (chave_acesso) WHERE chave_acesso IS NOT NULL AND ("
                    "data_cadastro IS NULL "
                    "OR data_cadastro < TIMESTAMP '2025-12-01 00:00:00' "
                    "OR data_cadastro >= TIMESTAMP '2026-07-01 00:00:00'"
                    ")"
                )
            )
        if "faturistas" in inspector.get_table_names():
            connection.execute(
                text(
                    "INSERT INTO faturistas (nome, ativo, data_cadastro) "
                    "SELECT 'BIPE', 1, CURRENT_TIMESTAMP "
                    "WHERE NOT EXISTS (SELECT 1 FROM faturistas WHERE nome = 'BIPE')"
                )
            )
    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "role" not in user_columns:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN role {string_type} DEFAULT 'user'"))
        if "module_access" not in user_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN module_access TEXT"))
        with engine.begin() as connection:
            connection.execute(text("UPDATE users SET module_access = :modules WHERE LOWER(username) = 'mauro' AND module_access IS NULL"), {"modules": '["notes", "reports", "tme", "tmac"]'})
            connection.execute(
                text(
                    "UPDATE users SET module_access = :modules "
                    "WHERE LOWER(username) = 'viewer_user' "
                    "AND (module_access IS NULL OR TRIM(module_access) IN ('', '[\"notes\"]'))"
                ),
                {"modules": '["notes", "reports", "tme", "tmac"]'},
            )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
