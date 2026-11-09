"""Tabelas exclusivas do planejamento mensal, sem alterar notas fiscais."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base
from .time_utils import local_now


class MetaMes(Base):
    __tablename__ = "metas_meses"
    __table_args__ = (
        UniqueConstraint("tipo", "ano", "mes", name="uq_metas_mes_tipo_periodo"),
        CheckConstraint("tipo IN ('expedicao', 'recebimento')", name="ck_metas_mes_tipo"),
        CheckConstraint("ano BETWEEN 2000 AND 2100 AND mes BETWEEN 1 AND 12", name="ck_metas_mes_periodo"),
    )

    id = Column(Integer, primary_key=True)
    tipo = Column(String(20), nullable=False)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    versao = Column(Integer, nullable=False, default=1)
    criado_em = Column(DateTime, nullable=False, default=local_now)
    atualizado_em = Column(DateTime, nullable=False, default=local_now)
    atualizado_por = Column(String(100), nullable=False)
    dias = relationship("MetaDia", cascade="all, delete-orphan", order_by="MetaDia.data", lazy="select")


class MetaDia(Base):
    __tablename__ = "metas_dias"
    __table_args__ = (
        UniqueConstraint("mes_id", "data", name="uq_metas_dia_mes_data"),
        CheckConstraint("meta_a1br IS NULL OR meta_a1br >= 0", name="ck_metas_dia_a1br"),
        CheckConstraint("meta_a2br IS NULL OR meta_a2br >= 0", name="ck_metas_dia_a2br"),
    )

    id = Column(Integer, primary_key=True)
    mes_id = Column(Integer, ForeignKey("metas_meses.id", ondelete="CASCADE"), nullable=False, index=True)
    data = Column(Date, nullable=False)
    meta_a1br = Column(Numeric(15, 3), nullable=True)
    meta_a2br = Column(Numeric(15, 3), nullable=True)
    ajuste_a1br = Column(Numeric(15, 3), nullable=True)
    ajuste_a2br = Column(Numeric(15, 3), nullable=True)
