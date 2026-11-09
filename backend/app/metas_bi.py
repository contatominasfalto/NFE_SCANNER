"""Camada SQL exclusiva de Metas para Power BI; nao concede acesso publico."""

from pathlib import Path

from sqlalchemy import text


VIEW_NAMES = ("vw_metas", "vw_metas_expedicao", "vw_metas_recebimento")
SQL_PATH = Path(__file__).with_name("metas_bi.sql")


def apply_metas_bi_views(connection):
    if connection.dialect.name != "postgresql":
        raise ValueError("A integracao Power BI de Metas exige PostgreSQL.")
    # Arquivo controlado pelo projeto, sem parametros ou SQL fornecido pelo usuario.
    # As instrucoes nao contem funcoes com ponto e virgula interno.
    for statement in SQL_PATH.read_text(encoding="utf-8").split(";"):
        if statement.strip():
            connection.execute(text(statement))


def ensure_metas_bi_views(engine):
    if engine.dialect.name != "postgresql":
        return False
    with engine.begin() as connection:
        apply_metas_bi_views(connection)
    return True


def metas_bi_status(db):
    if db.get_bind().dialect.name != "postgresql":
        raise ValueError("A integracao Power BI de Metas exige PostgreSQL.")
    counts = [
        {"nome": f"powerbi.{name}", "linhas": db.execute(text(f"SELECT COUNT(*) FROM powerbi.{name}")).scalar_one()}
        for name in VIEW_NAMES
    ]
    return {
        "versao": "metas_bi_v1",
        "banco": db.execute(text("SELECT current_database()")).scalar_one(),
        "unidade": "toneladas",
        "views": counts,
        "credencial_bi": "Criar separadamente com scripts/preparar_metas_bi.py; este diagnostico nao confirma a existencia do login.",
    }
