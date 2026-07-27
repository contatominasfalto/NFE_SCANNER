-- NFE Scanner - Camada de dados para Power BI
--
-- Onde aplicar:
-- PostgreSQL do Render, usando a External Database URL com sslmode=require.
--
-- Objetivo:
-- 1. Criar um schema separado chamado powerbi.
-- 2. Criar views prontas para consumo no Power BI.
-- 3. Opcionalmente criar um usuario somente leitura para o Power BI.
--
-- Importante:
-- - Troque TROQUE_POR_UMA_SENHA_FORTE antes de executar o bloco de usuario.
-- - Se o Render/PostgreSQL nao permitir CREATE ROLE, crie apenas as views e use
--   temporariamente a credencial do banco no Power BI, ou crie uma credencial pelo
--   painel do Render.

BEGIN;

CREATE SCHEMA IF NOT EXISTS powerbi;

CREATE OR REPLACE VIEW powerbi.vw_notas_fiscais AS
SELECT
    nf.id,
    nf.chave_acesso,
    nf.numero_nf,
    CASE
        WHEN nf.numero_nf ~ '^[0-9]+$' THEN nf.numero_nf::integer
        ELSE NULL
    END AS numero_nf_int,
    nf.serie,
    nf.data_cadastro AS data_hora_bip,
    nf.data_cadastro::date AS data_bip,
    nf.data_cadastro::time AS hora_bip,
    nf.data_emissao AS data_hora_emissao,
    nf.data_emissao::date AS data_emissao,
    nf.data_emissao::time AS hora_emissao,
    nf.cnpj_fornecedor,
    nf.nome_fornecedor,
    nf.local,
    nf.produto AS material,
    nf.quantidade AS quantidade_kg,
    (COALESCE(nf.quantidade, 0) / 1000.0) AS quantidade_ton,
    nf.valor_total,
    nf.transportador,
    nf.faturista AS usuario_lancamento,
    nf.lider_operacional,
    nf.observacao,
    nf.erro_salvamento,
    nf.erro_detalhe,
    CASE
        WHEN COALESCE(nf.erro_salvamento, FALSE)
          OR UPPER(COALESCE(nf.produto, '')) = 'ERRO'
          OR UPPER(COALESCE(nf.numero_nf, '')) = 'ERRO'
        THEN 'Com erro'
        ELSE 'Valida'
    END AS status_nota,
    CASE
        WHEN COALESCE(nf.erro_salvamento, FALSE)
          OR UPPER(COALESCE(nf.produto, '')) = 'ERRO'
          OR UPPER(COALESCE(nf.numero_nf, '')) = 'ERRO'
        THEN FALSE
        ELSE TRUE
    END AS nota_valida,
    EXTRACT(YEAR FROM nf.data_cadastro)::integer AS ano_bip,
    EXTRACT(MONTH FROM nf.data_cadastro)::integer AS mes_bip,
    EXTRACT(DAY FROM nf.data_cadastro)::integer AS dia_bip,
    EXTRACT(YEAR FROM nf.data_emissao)::integer AS ano_emissao,
    EXTRACT(MONTH FROM nf.data_emissao)::integer AS mes_emissao,
    EXTRACT(DAY FROM nf.data_emissao)::integer AS dia_emissao
FROM public.notas_fiscais nf;

CREATE OR REPLACE VIEW powerbi.vw_notas_validas AS
SELECT *
FROM powerbi.vw_notas_fiscais
WHERE nota_valida = TRUE;

CREATE OR REPLACE VIEW powerbi.vw_notas_com_erro AS
SELECT *
FROM powerbi.vw_notas_fiscais
WHERE nota_valida = FALSE;

CREATE OR REPLACE VIEW powerbi.vw_resumo_dia_bip AS
SELECT
    data_bip,
    COUNT(*) AS total_notas,
    COUNT(*) FILTER (WHERE nota_valida = TRUE) AS notas_validas,
    COUNT(*) FILTER (WHERE nota_valida = FALSE) AS notas_com_erro,
    SUM(CASE WHEN nota_valida THEN quantidade_kg ELSE 0 END) AS quantidade_kg,
    SUM(CASE WHEN nota_valida THEN quantidade_ton ELSE 0 END) AS quantidade_ton,
    SUM(CASE WHEN nota_valida THEN COALESCE(valor_total, 0) ELSE 0 END) AS valor_total
FROM powerbi.vw_notas_fiscais
GROUP BY data_bip;

CREATE OR REPLACE VIEW powerbi.vw_resumo_dia_emissao AS
SELECT
    data_emissao,
    COUNT(*) AS total_notas,
    COUNT(*) FILTER (WHERE nota_valida = TRUE) AS notas_validas,
    COUNT(*) FILTER (WHERE nota_valida = FALSE) AS notas_com_erro,
    SUM(CASE WHEN nota_valida THEN quantidade_kg ELSE 0 END) AS quantidade_kg,
    SUM(CASE WHEN nota_valida THEN quantidade_ton ELSE 0 END) AS quantidade_ton,
    SUM(CASE WHEN nota_valida THEN COALESCE(valor_total, 0) ELSE 0 END) AS valor_total
FROM powerbi.vw_notas_fiscais
GROUP BY data_emissao;

CREATE OR REPLACE VIEW powerbi.vw_resumo_material AS
SELECT
    material,
    COUNT(*) AS total_notas,
    SUM(quantidade_kg) AS quantidade_kg,
    SUM(quantidade_ton) AS quantidade_ton,
    SUM(COALESCE(valor_total, 0)) AS valor_total
FROM powerbi.vw_notas_validas
GROUP BY material;

CREATE OR REPLACE VIEW powerbi.vw_resumo_material_local AS
SELECT
    material,
    local,
    COUNT(*) AS total_notas,
    SUM(quantidade_kg) AS quantidade_kg,
    SUM(quantidade_ton) AS quantidade_ton,
    SUM(COALESCE(valor_total, 0)) AS valor_total
FROM powerbi.vw_notas_validas
GROUP BY material, local;

CREATE OR REPLACE VIEW powerbi.vw_resumo_usuario AS
SELECT
    usuario_lancamento,
    COUNT(*) AS total_notas,
    COUNT(*) FILTER (WHERE nota_valida = TRUE) AS notas_validas,
    COUNT(*) FILTER (WHERE nota_valida = FALSE) AS notas_com_erro,
    SUM(CASE WHEN nota_valida THEN quantidade_kg ELSE 0 END) AS quantidade_kg,
    SUM(CASE WHEN nota_valida THEN quantidade_ton ELSE 0 END) AS quantidade_ton
FROM powerbi.vw_notas_fiscais
GROUP BY usuario_lancamento;

CREATE OR REPLACE VIEW powerbi.vw_usuarios AS
SELECT
    id,
    username,
    role,
    active,
    created_at
FROM public.users;

CREATE OR REPLACE VIEW powerbi.vw_auditoria AS
SELECT
    id,
    created_at AS data_hora_evento,
    created_at::date AS data_evento,
    usuario,
    acao,
    area,
    entidade,
    entidade_id,
    descricao,
    detalhes
FROM public.audit_logs;

COMMIT;

-- Opcional: usuario somente leitura para o Power BI.
-- Execute este bloco separado depois de trocar a senha.
--
-- CREATE ROLE powerbi_nfe LOGIN PASSWORD 'TROQUE_POR_UMA_SENHA_FORTE';
-- GRANT CONNECT ON DATABASE nfe_scanner TO powerbi_nfe;
-- GRANT USAGE ON SCHEMA powerbi TO powerbi_nfe;
-- GRANT SELECT ON ALL TABLES IN SCHEMA powerbi TO powerbi_nfe;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA powerbi GRANT SELECT ON TABLES TO powerbi_nfe;

