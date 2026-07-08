CREATE DATABASE IF NOT EXISTS nfe_scanner
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'nfe_app'@'localhost' IDENTIFIED BY 'troque_esta_senha';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX
  ON nfe_scanner.* TO 'nfe_app'@'localhost';
FLUSH PRIVILEGES;

USE nfe_scanner;

CREATE TABLE IF NOT EXISTS notas_fiscais (
  id INT NOT NULL AUTO_INCREMENT,
  numero_nf VARCHAR(255) NULL,
  serie VARCHAR(255) NULL,
  data_emissao DATETIME NULL,
  cnpj_fornecedor VARCHAR(255) NULL,
  nome_fornecedor VARCHAR(255) NULL,
  valor_total DOUBLE NULL,
  chave_acesso VARCHAR(255) NULL,
  local VARCHAR(255) NULL,
  produto TEXT NULL,
  quantidade DOUBLE NULL,
  transportador VARCHAR(255) NULL,
  faturista VARCHAR(255) NULL DEFAULT 'BIPE',
  lider_operacional VARCHAR(255) NULL,
  observacao TEXT NULL,
  erro_salvamento BOOLEAN NOT NULL DEFAULT FALSE,
  erro_detalhe TEXT NULL,
  caminho_arquivo_imagem VARCHAR(255) NULL,
  data_cadastro DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY ix_notas_fiscais_chave_acesso (chave_acesso),
  KEY ix_notas_fiscais_numero_nf (numero_nf),
  KEY ix_notas_fiscais_cnpj_fornecedor (cnpj_fornecedor),
  KEY ix_notas_fiscais_nome_fornecedor (nome_fornecedor),
  KEY ix_notas_fiscais_local (local)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  salt VARCHAR(255) NOT NULL,
  role VARCHAR(255) NOT NULL DEFAULT 'user',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY ix_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
