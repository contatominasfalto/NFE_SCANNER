import os
import psycopg2
from datetime import datetime

CHAVE = "31260833592510044798550020002892501011534783"
DATA_ESPERADA = datetime(2026, 8, 3, 6, 38, 58)
DATA_NOVA = datetime(2026, 8, 2, 6, 38, 58)

conn = psycopg2.connect(os.environ["DB_URL"])
conn.autocommit = False

try:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, numero_nf, data_cadastro
            FROM notas_fiscais
            WHERE chave_acesso = %s
            FOR UPDATE
            """,
            (CHAVE,)
        )

        row = cur.fetchone()

        if not row:
            raise Exception("Nota nao encontrada.")

        nota_id, numero_nf, data_atual = row

        print(f"Nota encontrada: ID={nota_id} NF={numero_nf}")
        print(f"Data atual: {data_atual}")

        if data_atual.replace(microsecond=0) != DATA_ESPERADA:
            raise Exception(
                f"ABORTADO: data atual nao confere. Banco={data_atual} | Esperado={DATA_ESPERADA}"
            )

        cur.execute(
            """
            UPDATE notas_fiscais
            SET data_cadastro = %s
            WHERE id = %s
            """,
            (DATA_NOVA, nota_id)
        )

        cur.execute(
            """
            INSERT INTO audit_logs (
                created_at, usuario, acao, area, entidade, entidade_id, descricao, detalhes
            )
            VALUES (
                NOW() AT TIME ZONE 'America/Sao_Paulo',
                'ajuste_manual',
                'Ajustou data de bip manualmente',
                'Notas fiscais',
                'NotaFiscal',
                %s,
                'Alterou data_cadastro diretamente no banco por solicitacao operacional.',
                %s
            )
            """,
            (
                str(nota_id),
                f"Chave: {CHAVE} | Antes: {DATA_ESPERADA} | Depois: {DATA_NOVA}"
            )
        )

        conn.commit()

        print("AJUSTE CONCLUIDO COM SUCESSO")
        print(f"Nova data do bip: {DATA_NOVA}")

except Exception as e:
    conn.rollback()
    print(str(e))
    print("Nenhuma alteracao foi salva.")

finally:
    conn.close()
