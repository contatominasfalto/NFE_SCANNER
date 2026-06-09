from sqlalchemy import Column, Integer, String, Float, DateTime, Text
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
    centro_custo = Column(String, index=True, nullable=True)
    produto = Column(Text)
    quantidade = Column(Float)
    local_areia = Column(String)
    transportador = Column(String)
    faturista = Column(String, default="BIPE")
    lider_operacional = Column(String)
    observacao = Column(Text)
    caminho_arquivo_imagem = Column(String)
    data_cadastro = Column(DateTime, default=datetime.now)
