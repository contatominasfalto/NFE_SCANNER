from enum import Enum

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Local(str, Enum):
    CDMA = "CDMA"
    PRU = "PRU"


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
    erro_salvamento: bool = False
    erro_detalhe: Optional[str] = None
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
        examples=["CDMA"],
    )

class BarcodeResult(BaseModel):
    chave_acesso: str = Field(description="Chave de acesso NF-e validada com 44 digitos.")
    quantidade_digitos: int
    nota: NotaFiscalBase


class BarcodeBatchInput(BaseModel):
    local: Local = Field(description="Local onde o material das notas sera alocado.")
    chaves: list[str] = Field(min_length=1, description="Chaves de acesso NF-e ou leituras do scanner.")


class BarcodeBatchItem(BaseModel):
    chave_acesso: str
    status: str
    detalhe: str
    id: Optional[int] = None
    numero_nf: Optional[str] = None


class BarcodeBatchResponse(BaseModel):
    total: int
    cadastradas: int
    erros: int
    duplicadas: int
    invalidas: int
    itens: list[BarcodeBatchItem]


class NotaFiscalErrorCreate(BaseModel):
    chave_acesso: str = Field(min_length=1, max_length=100)
    local: Optional[str] = None
    detalhe: Optional[str] = Field(None, max_length=2000)
    faturista: str = "BIPE"


class NotaFiscalErrorRefreshItem(BaseModel):
    chave_acesso: str
    atualizado: bool
    detalhe: str


class NotaFiscalErrorRefreshResponse(BaseModel):
    encontradas: int
    atualizadas: int
    falhas: int
    itens: list[NotaFiscalErrorRefreshItem]


class RelatorioProduto(BaseModel):
    produto: str
    quantidade_ton: float


class RelatorioPeriodo(BaseModel):
    inicio: datetime
    fim: datetime
    total_ton: float
    total_notas: int
    produtos: list[RelatorioProduto]


class RelatorioOperacionalResponse(BaseModel):
    mes: RelatorioPeriodo
    dia: RelatorioPeriodo


class RelatorioMaterialItem(BaseModel):
    material: str
    quantidade_ton: float
    quantidade_nfes: int


class RelatorioMaterialResponse(BaseModel):
    inicio: datetime
    fim: datetime
    total_ton: float
    total_nfes: int
    materiais: list[RelatorioMaterialItem]


class RelatorioMaterialLocalItem(BaseModel):
    material: str
    quantidade_cdma_ton: float
    quantidade_nfes_cdma: int
    quantidade_pru_ton: float
    quantidade_nfes_pru: int


class RelatorioMaterialLocalResponse(BaseModel):
    inicio: datetime
    fim: datetime
    materiais: list[RelatorioMaterialLocalItem]


class RelatorioRecebimentoDia(BaseModel):
    data: str
    materiais_ton: dict[str, float]


class RelatorioRecebimentoMaterial(BaseModel):
    material: str
    total_ton: float


class RelatorioRecebimentoResponse(BaseModel):
    inicio: datetime
    fim: datetime
    material: Optional[str] = None
    materiais_disponiveis: list[str]
    totais_materiais: list[RelatorioRecebimentoMaterial]
    total_ton: float
    dias: list[RelatorioRecebimentoDia]


class NotaFiscalDeleteResponse(BaseModel):
    id: int
    numero_nf: str
    chave_acesso: Optional[str] = None
    mensagem: str


class FaturistaBase(BaseModel):
    nome: str = Field(min_length=2, max_length=100, examples=["Maria Silva"])
    ativo: bool = True


class FaturistaCreate(FaturistaBase):
    senha: str = Field(min_length=6, max_length=100, examples=["senha123"])


class FaturistaUpdate(FaturistaBase):
    senha: Optional[str] = Field(None, min_length=6, max_length=100)


class FaturistaResponse(FaturistaBase):
    id: int
    data_cadastro: datetime

    class Config:
        from_attributes = True


class FaturistaDeleteResponse(BaseModel):
    id: int
    nome: str
    mensagem: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    created_at: datetime
    usuario: str
    acao: str
    area: str
    entidade: Optional[str] = None
    entidade_id: Optional[str] = None
    descricao: str
    detalhes: Optional[str] = None

    class Config:
        from_attributes = True
