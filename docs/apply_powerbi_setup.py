from pathlib import Path
import os

from sqlalchemy import create_engine


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+"):
        return database_url

    if database_url.startswith("postgresql://"):
        try:
            import psycopg2  # noqa: F401

            return database_url
        except ModuleNotFoundError:
            import psycopg  # noqa: F401

            return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return database_url


def main() -> None:
    database_url = os.environ.get("PG_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit(
            "Defina PG_URL com a External Database URL do Render antes de executar."
        )

    database_url = normalize_database_url(database_url)

    sql_path = Path(__file__).with_name("powerbi_setup.sql")
    sql = sql_path.read_text(encoding="utf-8")

    engine = create_engine(database_url, pool_pre_ping=True)

    with engine.connect() as conn:
        conn.exec_driver_sql(sql)

    print("Views do Power BI aplicadas com sucesso.")


if __name__ == "__main__":
    main()
