from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NotaFiscalBase(BaseModel):
    numero_nf: str
    serie: str
    data_emissao: datetime
    cnpj_fornecedor: str
    nome_fornecedor: str
    valor_total: float
    chave_acesso: Optional[str] = None
    observacao: Optional[str] = None

class NotaFiscalCreate(NotaFiscalBase):
    caminho_arquivo_imagem: Optional[str] = None

class NotaFiscalResponse(NotaFiscalBase):
    id: int
    data_cadastro: datetime
    caminho_arquivo_imagem: Optional[str] = None

    class Config:
        from_attributes = True

class OCRResult(BaseModel):
    numero_nf: str
    serie: str
    data_emissao: datetime
    cnpj_fornecedor: str
    nome_fornecedor: str
    valor_total: float
    chave_acesso: str
    observacao: str
    caminho_arquivo_imagem: str
