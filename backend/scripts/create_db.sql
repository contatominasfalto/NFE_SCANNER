-- Banco de dados SQLite/PostgreSQL
CREATE TABLE IF NOT EXISTS notas_fiscais (
    id SERIAL PRIMARY KEY,
    numero_nf VARCHAR(50) NOT NULL,
    serie VARCHAR(10),
    data_emissao TIMESTAMP NOT NULL,
    cnpj_fornecedor VARCHAR(18),
    nome_fornecedor VARCHAR(200),
    valor_total DECIMAL(10,2),
    chave_acesso VARCHAR(44) UNIQUE,
    local VARCHAR(20),
    produto TEXT,
    quantidade REAL,
    transportador VARCHAR(255),
    faturista VARCHAR(100) DEFAULT 'BIPE',
    lider_operacional VARCHAR(255),
    observacao TEXT,
    caminho_arquivo_imagem VARCHAR(500),
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para otimização
CREATE INDEX idx_numero_nf ON notas_fiscais(numero_nf);
CREATE INDEX idx_cnpj ON notas_fiscais(cnpj_fornecedor);
CREATE INDEX idx_data_emissao ON notas_fiscais(data_emissao);

-- Dados de exemplo
INSERT INTO notas_fiscais (numero_nf, serie, data_emissao, cnpj_fornecedor, nome_fornecedor, valor_total, data_cadastro)
VALUES 
('123456', '1', '2024-01-15 10:00:00', '12.345.678/0001-90', 'Fornecedor Exemplo LTDA', 1500.00, CURRENT_TIMESTAMP),
('789012', '2', '2024-01-20 14:30:00', '98.765.432/0001-21', 'Materiais de Construção XYZ', 3200.50, CURRENT_TIMESTAMP);
