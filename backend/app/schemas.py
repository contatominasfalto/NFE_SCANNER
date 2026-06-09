from enum import Enum

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Local(str, Enum):
    A1BR = "A1BR"
    A1BR_PRU = "A1BR/PRU"
    A2BR = "A2BR"


class NotaFiscalBase(BaseModel):
    numero_nf: str
    serie: str
    data_emissao: datetime
    cnpj_fornecedor: str
    nome_fornecedor: str
    valor_total: float
    chave_acesso: Optional[str] = None
    local: Optional[Local] = None
    produto: Optional[str] = None
    quantidade: Optional[float] = None
    transportador: Optional[str] = None
    faturista: str = "BIPE"
    lider_operacional: Optional[str] = None
    observacao: Optional[str] = None

class NotaFiscalCreate(NotaFiscalBase):
    local: Local
    caminho_arquivo_imagem: Optional[str] = None

class NotaFiscalUpdate(NotaFiscalBase):
    caminho_arquivo_imagem: Optional[str] = None

class NotaFiscalResponse(NotaFiscalBase):
    id: int
    data_cadastro: datetime
    caminho_arquivo_imagem: Optional[str] = None

    class Config:
        from_attributes = True

class BarcodeInput(BaseModel):
    codigo_barras: str = Field(
        ...,
        description="Conteudo recebido do leitor. Pode conter espacos ou separadores; a API extrai os digitos.",
        examples=["31260506178118000190550010000222441113062139"],
    )

class BarcodeImportInput(BarcodeInput):
    local: Local = Field(
        description="Local onde o material da nota sera alocado.",
        examples=["A1BR"],
    )

class BarcodeResult(BaseModel):
    chave_acesso: str = Field(description="Chave de acesso NF-e validada com 44 digitos.")
    quantidade_digitos: int
    nota: NotaFiscalBase

class NotaFiscalDeleteResponse(BaseModel):
    id: int
    numero_nf: str
    chave_acesso: Optional[str] = None
    mensagem: str


class FaturistaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=100, examples=["Maria Silva"])


class FaturistaUpdate(FaturistaCreate):
    ativo: bool = True


class FaturistaResponse(FaturistaUpdate):
    id: int
    data_cadastro: datetime

    class Config:
        from_attributes = True


class FaturistaDeleteResponse(BaseModel):
    id: int
    nome: str
    mensagem: str
