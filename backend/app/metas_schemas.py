from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MetaTipo = Literal["expedicao", "recebimento"]
Toneladas = Annotated[Decimal, Field(max_digits=15, decimal_places=3, allow_inf_nan=False)]
MetaToneladas = Annotated[Decimal, Field(ge=0, max_digits=15, decimal_places=3, allow_inf_nan=False)]


class MetaDiaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: date
    meta_a1br: MetaToneladas | None = None
    meta_a2br: MetaToneladas | None = None
    ajuste_a1br: Toneladas | None = None
    ajuste_a2br: Toneladas | None = None


class MetaMesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ano: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    dias: list[MetaDiaInput] = Field(min_length=28, max_length=31)

    @model_validator(mode="after")
    def validar_calendario(self):
        expected = {date(self.ano, self.mes, day) for day in range(1, monthrange(self.ano, self.mes)[1] + 1)}
        if len(self.dias) != len(expected) or {day.data for day in self.dias} != expected:
            raise ValueError("Informe cada dia do mês exatamente uma vez, do primeiro ao último dia.")
        return self


class MetaMesUpdate(MetaMesInput):
    id: int = Field(ge=1)
    versao: int = Field(ge=1)


class MetaMesSummary(BaseModel):
    id: int
    tipo: MetaTipo
    ano: int
    mes: int
    versao: int
    atualizado_em: datetime
    atualizado_por: str


class MetaMesResponse(MetaMesSummary):
    dias: list[MetaDiaInput]
    totais: dict[str, Decimal]
