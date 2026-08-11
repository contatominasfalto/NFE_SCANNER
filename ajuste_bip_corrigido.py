import os
import psycopg2
from datetime import datetime


CHAVES = [
    "31260833592510044798550020002899991698040702",
    "31260833592510044798550020002899981991994970",
    "31260833592510044798550020002899971262552736",
    "31260833592510044798550020002899961051833835",
    "31260833592510044798550020002899951061114699",
    "31260833592510044798550020002899941684053312",
    "31260833592510044798550020002899931549969439",
    "31260833592510044798550020002899921917995400",
    "31260833592510044798550020002899911719408004",
    "31260833592510044798550020002899901493216960",
    "31260833592510044798550020002899891020022369",
    "31260833592510044798550020002899881261067061",
    "31260833592510044798550020002899871725930989",
    "31260833592510044798550020002899861996438412",
    "31260833592510044798550020002899851325206448",
    "31260833592510044798550020002899841063621705",
    "31260833592510044798550020002899831584863394",
    "31260833592510044798550020002899821868616351",
    "31260833592510044798550020002899811862073049",
    "31260833592510044798550020002899801467755232",
    "31260833592510044798550020002899791790194203",
    "31260833592510044798550020002900131884195850",
    "31260833592510044798550020002900121648483734",
    "31260833592510044798550020002900111425775762",
    "31260833592510044798550020002900101027659668",
    "31260833592510044798550020002900091345052952",
    "31260833592510044798550020002900081571531354",
    "31260833592510044798550020002900071717793296",
    "31260833592510044798550020002900061388339283",
    "31260833592510044798550020002900051032002876",
    "31260833592510044798550020002900041887563567",
    "31260833592510044798550020002900031937188082",
    "31260833592510044798550020002900021317682989",
    "31260833592510044798550020002900011937033963",
    "31260833592510044798550020002900001627982897",
]

DATA_ATUAL_ESPERADA = datetime(2026, 8, 7)
DATA_NOVA = datetime(2026, 8, 6)


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
