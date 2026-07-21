from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from .database import Base

class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id = Column(Integer, primary_key=True, index=True)
    numero_nf = Column(String(30), index=True)
    serie = Column(String(10))
    data_emissao = Column(DateTime)
    cnpj_fornecedor = Column(String(20), index=True)
    nome_fornecedor = Column(String(255), index=True)
    valor_total = Column(Float)
    chave_acesso = Column(String(44), unique=True, index=True)
    local = Column(String(20), index=True, nullable=True)
    produto = Column(Text)
    quantidade = Column(Float)
    transportador = Column(String(255))
    faturista = Column(String(100), default="BIPE")
    lider_operacional = Column(String(100))
    observacao = Column(Text)
    erro_salvamento = Column(Boolean, default=False, nullable=False)
    erro_detalhe = Column(Text)
    caminho_arquivo_imagem = Column(String(500))
    data_cadastro = Column(DateTime, default=datetime.now)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(String(30), default="user", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    @property
    def nome(self):
        return self.username

    @property
    def ativo(self):
        return self.active

    @property
    def data_cadastro(self):
        return self.created_at


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    usuario = Column(String(100), index=True)
    acao = Column(String(120), index=True)
    area = Column(String(120), index=True)
    entidade = Column(String(80), nullable=True)
    entidade_id = Column(String(80), nullable=True)
    descricao = Column(Text)
    detalhes = Column(Text, nullable=True)
