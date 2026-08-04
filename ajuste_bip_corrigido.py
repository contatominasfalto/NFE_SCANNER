import os
import psycopg2
from datetime import datetime


CHAVES = [
    "31260833592510044798550020002894291397447534",
    "31260833592510044798550020002894301307000340",
    "31260833592510044798550020002894311517139031",
    "31260833592510044798550020002894321922120135",
    "31260833592510044798550020002894331821374600",
    "31260833592510044798550020002894341617478905",
    "31260833592510044798550020002894351854395873",
    "31260833592510044798550020002894361203805876",
    "31260833592510044798550020002894371257424916",
    "31260833592510044798550020002894381523303027",
    "31260833592510044798550020002894391302806619",
    "31260833592510044798550020002894401049741217",
    "31260833592510044798550020002894421712826542",
    "31260833592510044798550020002894441010951341",
    "31260833592510044798550020002894411375203017",
    "31260833592510044798550020002894461650786428",
    "31260833592510044798550020002894451949503300",
    "31260833592510044798550020002894431329249420",
    "31260833592510044798550020002894481347298310",
    "31260833592510044798550020002894471760428469",
    "31260833592510044798550020002894491334118870",
    "31260833592510044798550020002894501196035100",
    "31260833592510044798550020002894511454952426",
    "31260833592510044798550020002894521525858734",
    "31260833592510044798550020002894531627777625",
    "31260833592510044798550020002894541513846366",
    "31260833592510044798550020002894551661240870",
    "31260833592510044798550020002894561306155613",
    "31260833592510044798550020002894571095594784",
    "31260833592510044798550020002894581687798226",
    "31260833592510044798550020002894591637384433",
]

DATA_ATUAL_ESPERADA = datetime(2026, 8, 4)
DATA_NOVA = datetime(2026, 8, 3)


def processar_chave(conn, chave):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, numero_nf, data_cadastro
            FROM notas_fiscais
            WHERE chave_acesso = %s
            FOR UPDATE
            """,
            (chave,),
        )
        row = cur.fetchone()

        if not row:
            return False, f"Nota nao encontrada para chave: {chave}"

        nota_id, numero_nf, data_atual = row
        data_atual_sem_hora = data_atual.replace(hour=0, minute=0, second=0, microsecond=0)
        data_esperada_sem_hora = DATA_ATUAL_ESPERADA.replace(hour=0, minute=0, second=0, microsecond=0)

        if data_atual_sem_hora != data_esperada_sem_hora:
            return False, (
                f"ABORTADO: data atual nao confere para NF {numero_nf}. "
                f"Banco={data_atual.date()} | Esperado={DATA_ATUAL_ESPERADA.date()}"
            )

        data_nova = datetime(
            DATA_NOVA.year,
            DATA_NOVA.month,
            DATA_NOVA.day,
            data_atual.hour,
            data_atual.minute,
            data_atual.second,
            data_atual.microsecond,
        )

        cur.execute(
            """
            UPDATE notas_fiscais
            SET data_cadastro = %s
            WHERE id = %s
            """,
            (data_nova, nota_id),
        )

        cur.execute(
            """
            INSERT INTO audit_logs (
                created_at, usuario, acao, area, entidade, entidade_id,
                descricao, detalhes
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
                f"Chave: {chave} | NF: {numero_nf} | Antes: {data_atual} | Depois: {data_nova}",
            ),
        )

        return True, f"SUCESSO: NF {numero_nf} atualizada de {data_atual} para {data_nova}"


def main():
    try:
        conn = psycopg2.connect(os.environ["DB_URL"])
        conn.autocommit = False
    except Exception as error:
        print(f"ERRO ao conectar ao banco: {error}")
        return

    try:
        print(f"Iniciando processamento de {len(CHAVES)} notas fiscais...")
        print(f"Data atual esperada: {DATA_ATUAL_ESPERADA.date()}")
        print(f"Nova data desejada: {DATA_NOVA.date()}")
        print("ATENCAO: o horario original de cada nota sera mantido.")
        print("-" * 60)

        resultados = []
        sucessos = 0
        falhas = 0

        for i, chave in enumerate(CHAVES, 1):
            print(f"\n[{i}/{len(CHAVES)}] Processando chave: {chave}")
            try:
                sucesso, mensagem = processar_chave(conn, chave)
            except Exception as error:
                sucesso = False
                mensagem = f"ERRO ao processar chave {chave}: {error}"

            resultados.append((chave, sucesso, mensagem))

            if sucesso:
                sucessos += 1
                print(f"OK - {mensagem}")
            else:
                falhas += 1
                print(f"FALHA - {mensagem}")

        if falhas == 0:
            conn.commit()
            print("\n" + "=" * 60)
            print("TODAS AS OPERACOES CONCLUIDAS COM SUCESSO!")
            print(f"Total de notas processadas: {sucessos}")
        else:
            conn.rollback()
            print("\n" + "=" * 60)
            print("OPERACAO CANCELADA - Falhas detectadas")
            print(f"Sucessos: {sucessos}")
            print(f"Falhas: {falhas}")
            print("Nenhuma alteracao foi salva devido a falhas.")
            print("\nDetalhes das falhas:")
            for chave, sucesso, mensagem in resultados:
                if not sucesso:
                    print(f"  - Chave: {chave}")
                    print(f"    Erro: {mensagem}")

    except Exception as error:
        conn.rollback()
        print(f"\nERRO GERAL: {error}")
        print("Nenhuma alteracao foi salva.")
    finally:
        conn.close()
        print("\nConexao com banco encerrada.")


if __name__ == "__main__":
    main()
