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
    observacao = Column(Text)
    caminho_arquivo_imagem = Column(String)
    data_cadastro = Column(DateTime, default=datetime.now)