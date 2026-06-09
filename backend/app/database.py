from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def ensure_schema():
    inspector = inspect(engine)
    if "notas_fiscais" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("notas_fiscais")}
    migrations = {
        "centro_custo": "ALTER TABLE notas_fiscais ADD COLUMN centro_custo VARCHAR",
        "produto": "ALTER TABLE notas_fiscais ADD COLUMN produto TEXT",
        "quantidade": "ALTER TABLE notas_fiscais ADD COLUMN quantidade FLOAT",
        "local_areia": "ALTER TABLE notas_fiscais ADD COLUMN local_areia VARCHAR",
        "transportador": "ALTER TABLE notas_fiscais ADD COLUMN transportador VARCHAR",
        "faturista": "ALTER TABLE notas_fiscais ADD COLUMN faturista VARCHAR DEFAULT 'BIPE'",
        "lider_operacional": "ALTER TABLE notas_fiscais ADD COLUMN lider_operacional VARCHAR",
    }
    with engine.begin() as connection:
        for column, statement in migrations.items():
            if column not in columns:
                connection.execute(text(statement))
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_notas_fiscais_centro_custo "
                "ON notas_fiscais (centro_custo)"
            )
        )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
