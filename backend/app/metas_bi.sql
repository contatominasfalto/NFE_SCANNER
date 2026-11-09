-- Metas em toneladas. Uma linha por data, operacao e unidade.
-- Usar dentro de uma transacao. Nao altera metas nem permissao de usuarios.
CREATE SCHEMA IF NOT EXISTS powerbi;

CREATE OR REPLACE VIEW powerbi.vw_metas AS
SELECT
    m.id AS mes_id,
    d.id AS dia_id,
    d.data,
    m.ano,
    m.mes,
    make_date(m.ano, m.mes, 1) AS competencia,
    m.tipo AS operacao,
    'A1BR'::text AS unidade,
    d.meta_a1br AS meta_ton,
    CASE WHEN m.tipo = 'recebimento' THEN d.ajuste_a1br ELSE NULL::numeric(15,3) END AS ajuste_ton,
    d.meta_a1br IS NOT NULL AS meta_informada,
    (m.tipo = 'recebimento' AND d.ajuste_a1br IS NOT NULL) AS ajuste_informado,
    m.versao,
    m.atualizado_em,
    m.atualizado_por
FROM public.metas_meses m
JOIN public.metas_dias d ON d.mes_id = m.id
UNION ALL
SELECT
    m.id AS mes_id,
    d.id AS dia_id,
    d.data,
    m.ano,
    m.mes,
    make_date(m.ano, m.mes, 1) AS competencia,
    m.tipo AS operacao,
    'A2BR'::text AS unidade,
    d.meta_a2br AS meta_ton,
    CASE WHEN m.tipo = 'recebimento' THEN d.ajuste_a2br ELSE NULL::numeric(15,3) END AS ajuste_ton,
    d.meta_a2br IS NOT NULL AS meta_informada,
    (m.tipo = 'recebimento' AND d.ajuste_a2br IS NOT NULL) AS ajuste_informado,
    m.versao,
    m.atualizado_em,
    m.atualizado_por
FROM public.metas_meses m
JOIN public.metas_dias d ON d.mes_id = m.id;

CREATE OR REPLACE VIEW powerbi.vw_metas_expedicao AS
SELECT * FROM powerbi.vw_metas WHERE operacao = 'expedicao';

CREATE OR REPLACE VIEW powerbi.vw_metas_recebimento AS
SELECT * FROM powerbi.vw_metas WHERE operacao = 'recebimento';
