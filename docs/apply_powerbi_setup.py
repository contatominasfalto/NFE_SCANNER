from pathlib import Path
import os

from sqlalchemy import create_engine


def main() -> None:
    database_url = os.environ.get("PG_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit(
            "Defina PG_URL com a External Database URL do Render antes de executar."
        )

    sql_path = Path(__file__).with_name("powerbi_setup.sql")
    sql = sql_path.read_text(encoding="utf-8")

    engine = create_engine(database_url, pool_pre_ping=True)

    with engine.connect() as conn:
        conn.exec_driver_sql(sql)

    print("Views do Power BI aplicadas com sucesso.")


if __name__ == "__main__":
    main()
