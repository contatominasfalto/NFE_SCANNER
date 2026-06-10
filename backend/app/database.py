from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL

connect_args = {"check_same_thread": False, "timeout": 30} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

if DATABASE_URL.startswith("sqlite"):
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
    migrations = {
        "local": "ALTER TABLE notas_fiscais ADD COLUMN local VARCHAR",
        "produto": "ALTER TABLE notas_fiscais ADD COLUMN produto TEXT",
        "quantidade": "ALTER TABLE notas_fiscais ADD COLUMN quantidade FLOAT",
        "transportador": "ALTER TABLE notas_fiscais ADD COLUMN transportador VARCHAR",
        "faturista": "ALTER TABLE notas_fiscais ADD COLUMN faturista VARCHAR DEFAULT 'BIPE'",
        "lider_operacional": "ALTER TABLE notas_fiscais ADD COLUMN lider_operacional VARCHAR",
        "erro_salvamento": "ALTER TABLE notas_fiscais ADD COLUMN erro_salvamento BOOLEAN DEFAULT 0 NOT NULL",
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
        connection.execute(text("DROP INDEX IF EXISTS ix_notas_fiscais_centro_custo"))
        if "centro_custo" in columns:
            connection.execute(text("ALTER TABLE notas_fiscais DROP COLUMN centro_custo"))
        if "local_areia" in columns:
            connection.execute(text("ALTER TABLE notas_fiscais DROP COLUMN local_areia"))
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_notas_fiscais_local "
                "ON notas_fiscais (local)"
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
                connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
