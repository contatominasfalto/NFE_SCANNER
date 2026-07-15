from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from .database import Base

class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id = Column(Integer, primary_key=True, index=True)
    numero_nf = Column(String, index=True)
    serie = Column(String)
    data_emissao = Column(DateTime)
    cnpj_fornecedor = Column(String, index=True)
    nome_fornecedor = Column(String, index=True)
    valor_total = Column(Float)
    chave_acesso = Column(String, unique=True, index=True)
    local = Column(String, index=True, nullable=True)
    produto = Column(Text)
    quantidade = Column(Float)
    transportador = Column(String)
    faturista = Column(String, default="BIPE")
    lider_operacional = Column(String)
    observacao = Column(Text)
    erro_salvamento = Column(Boolean, default=False, nullable=False)
    erro_detalhe = Column(Text)
    caminho_arquivo_imagem = Column(String)
    data_cadastro = Column(DateTime, default=datetime.now)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
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
    usuario = Column(String, index=True)
    acao = Column(String, index=True)
    area = Column(String, index=True)
    entidade = Column(String, nullable=True)
    entidade_id = Column(String, nullable=True)
    descricao = Column(Text)
    detalhes = Column(Text, nullable=True)
