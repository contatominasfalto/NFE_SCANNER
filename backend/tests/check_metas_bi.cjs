// Validacao PostgreSQL isolada em WASM. Nenhuma conexao de rede ou banco real.
// Instalar @electric-sql/pglite em diretorio temporario e apontar NODE_PATH para node_modules.
const { PGlite } = require('@electric-sql/pglite');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
    const db = new PGlite();
    await db.exec(`
        CREATE TABLE public.metas_meses (
            id integer PRIMARY KEY, tipo text, ano integer, mes integer,
            versao integer, atualizado_em timestamp, atualizado_por text
        );
        CREATE TABLE public.metas_dias (
            id integer PRIMARY KEY, mes_id integer REFERENCES public.metas_meses(id) ON DELETE CASCADE,
            data date, meta_a1br numeric(15,3), meta_a2br numeric(15,3),
            ajuste_a1br numeric(15,3), ajuste_a2br numeric(15,3)
        );
        INSERT INTO public.metas_meses VALUES
            (1,'expedicao',2026,11,1,'2026-11-09 09:00','teste'),
            (2,'recebimento',2026,11,1,'2026-11-09 10:00','teste');
        INSERT INTO public.metas_dias VALUES
            (1,1,'2026-11-01',1200.125,0,9,9),
            (2,1,'2026-11-02',NULL,NULL,NULL,NULL),
            (3,2,'2026-11-01',10.000,20.000,-0.125,2.000);
    `);
    const sql = fs.readFileSync(path.join(__dirname, '../app/metas_bi.sql'), 'utf8');
    for (let repeat = 0; repeat < 2; repeat++) {
        await db.exec(`BEGIN; ${sql} COMMIT;`);
    }
    const all = (await db.query('SELECT * FROM powerbi.vw_metas ORDER BY dia_id, unidade')).rows;
    assert.equal(all.length, 6);
    assert.deepEqual(all.map(row => row.unidade), ['A1BR','A2BR','A1BR','A2BR','A1BR','A2BR']);
    assert.equal(all[0].meta_ton, '1200.125');
    assert.equal(all[1].meta_ton, '0.000');
    assert.equal(all[1].meta_informada, true);
    assert.equal(all[2].meta_ton, null);
    assert.equal(all[2].meta_informada, false);
    assert.equal(all[0].ajuste_ton, null);
    assert.equal(all[0].ajuste_informado, false);
    assert.equal(all[4].ajuste_ton, '-0.125');
    const shipping = (await db.query('SELECT COUNT(*)::int AS n, SUM(meta_ton)::text AS total FROM powerbi.vw_metas_expedicao')).rows[0];
    assert.deepEqual(shipping, { n: 4, total: '1200.125' });
    const receiving = (await db.query('SELECT COUNT(*)::int AS n, SUM(meta_ton)::text AS metas, SUM(ajuste_ton)::text AS ajustes FROM powerbi.vw_metas_recebimento')).rows[0];
    assert.deepEqual(receiving, { n: 2, metas: '30.000', ajustes: '1.875' });
    await db.exec(`
        CREATE ROLE bi_metas_teste LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
        GRANT USAGE ON SCHEMA powerbi TO bi_metas_teste;
        GRANT SELECT ON powerbi.vw_metas, powerbi.vw_metas_expedicao, powerbi.vw_metas_recebimento TO bi_metas_teste;
        SET ROLE bi_metas_teste;
    `);
    assert.equal((await db.query('SELECT COUNT(*)::int AS n FROM powerbi.vw_metas')).rows[0].n, 6);
    for (const operation of [
        'SELECT * FROM public.metas_dias',
        'SELECT * FROM public.metas_meses',
        'UPDATE public.metas_dias SET meta_a1br = 99',
        'DELETE FROM public.metas_dias',
        'UPDATE powerbi.vw_metas SET meta_ton = 99',
    ]) {
        await assert.rejects(db.query(operation));
    }
    await db.exec('RESET ROLE');
    // Executar a verificacao real do provisionador, inclusive privilegios PUBLIC
    // em colunas e em outras views, que nao devem passar despercebidos.
    const provisionSource = fs.readFileSync(path.join(__dirname, '../../scripts/preparar_metas_bi.py'), 'utf8');
    const accessSql = provisionSource.match(/broad_access = connection.execute\(text\("""([\s\S]*?)"""\)/)[1]
        .replaceAll(':role', '$1').replaceAll(':views', '$2');
    const checkAccess = () => db.query(accessSql, ['bi_metas_teste', ['vw_metas', 'vw_metas_expedicao', 'vw_metas_recebimento']]);
    assert.equal((await checkAccess()).rows.length, 0);
    await db.exec('GRANT SELECT (meta_a1br) ON public.metas_dias TO PUBLIC');
    assert.equal((await checkAccess()).rows.length, 1);
    await db.exec('REVOKE SELECT (meta_a1br) ON public.metas_dias FROM PUBLIC');
    await db.exec('CREATE VIEW powerbi.outra_view AS SELECT * FROM public.metas_dias; GRANT SELECT ON powerbi.outra_view TO PUBLIC');
    assert.equal((await checkAccess()).rows.length, 1);
    await db.exec('REVOKE SELECT ON powerbi.outra_view FROM PUBLIC');
    assert.equal((await checkAccess()).rows.length, 0);
    await db.exec('UPDATE public.metas_dias SET meta_a1br = 1300.125 WHERE id = 1');
    assert.equal((await db.query("SELECT meta_ton FROM powerbi.vw_metas WHERE dia_id=1 AND unidade='A1BR'")).rows[0].meta_ton, '1300.125');
    await db.exec('DELETE FROM public.metas_meses WHERE id = 1');
    assert.equal((await db.query('SELECT COUNT(*)::int AS n FROM powerbi.vw_metas_expedicao')).rows[0].n, 0);
    assert.equal((await db.query('SELECT COUNT(*)::int AS n FROM powerbi.vw_metas_recebimento')).rows[0].n, 2);
    await db.close();
    console.log('OK PostgreSQL isolado: SQL real, idempotencia, toneladas, null/zero, filtros, ajustes, atualizacao, exclusao e permissoes de leitura.');
})().catch(error => { console.error(error); process.exitCode = 1; });
