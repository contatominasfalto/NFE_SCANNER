"""CRUD de metas e auditoria confirmados na mesma transação."""

import json
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .metas_models import MetaDia, MetaMes
from .metas_schemas import MetaMesInput
from .models import AuditLog
from .time_utils import local_now


FIELDS = ("meta_a1br", "meta_a2br", "ajuste_a1br", "ajuste_a2br")


def summary(month):
    return {key: getattr(month, key) for key in ("id", "tipo", "ano", "mes", "versao", "atualizado_em", "atualizado_por")}


def month_payload(month):
    days = [{"data": day.data, **{field: getattr(day, field) for field in FIELDS}} for day in month.dias]
    totals = {field: sum((getattr(day, field) or Decimal("0") for day in month.dias), Decimal("0")) for field in FIELDS}
    totals["meta_geral"] = totals["meta_a1br"] + totals["meta_a2br"]
    totals["ajuste_geral"] = totals["ajuste_a1br"] + totals["ajuste_a2br"]
    return {**summary(month), "dias": days, "totais": totals}


def find_month(db: Session, tipo, ano, mes, *, lock=False):
    query = db.query(MetaMes).filter_by(tipo=tipo, ano=ano, mes=mes)
    if lock:
        query = query.with_for_update()
    month = query.first()
    if not month:
        raise HTTPException(404, "Mês não cadastrado nesta operação.")
    return month


def check_version(month, version, expected_id):
    if month.versao != version or month.id != expected_id:
        raise HTTPException(409, "Este mês foi alterado por outro usuário. Recarregue os dados antes de editar novamente.")


def validate_operation(tipo, payload):
    if tipo == "expedicao" and any(day.ajuste_a1br is not None or day.ajuste_a2br is not None for day in payload.dias):
        raise HTTPException(422, "Ajustes são permitidos somente em Recebimento.")


def audit(db, month, username, action, before, after):
    db.add(AuditLog(
        usuario=username, acao=action, area="Metas", entidade="MetaMes", entidade_id=str(month.id),
        descricao=f"{action}: {month.tipo}, {month.mes:02d}/{month.ano}.",
        detalhes=json.dumps({"unidade": "toneladas", "antes": before, "depois": after}, default=str, ensure_ascii=False),
    ))


def save_month(db: Session, tipo: str, payload: MetaMesInput, username: str, *, editing=False):
    validate_operation(tipo, payload)
    before = None
    if editing:
        month = find_month(db, tipo, payload.ano, payload.mes, lock=True)
        check_version(month, payload.versao, payload.id)
        before = month_payload(month)
        month.versao += 1
        existing = {day.data: day for day in month.dias}
        for day in payload.dias:
            row = existing[day.data]
            for field in FIELDS:
                setattr(row, field, getattr(day, field))
    else:
        month = MetaMes(tipo=tipo, ano=payload.ano, mes=payload.mes, versao=1, atualizado_por=username)
        month.dias = [MetaDia(**day.model_dump()) for day in sorted(payload.dias, key=lambda day: day.data)]
        db.add(month)
    month.atualizado_em = local_now()
    month.atualizado_por = username
    try:
        db.flush()
        result = month_payload(month)
        audit(db, month, username, "Editou metas" if editing else "Cadastrou metas", before, result)
        db.commit()
        return result
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Já existe um planejamento para este mês e operação. Recarregue a lista de meses.") from exc
    except Exception:
        db.rollback()
        raise


def delete_month(db: Session, tipo, ano, mes, version, expected_id, username):
    month = find_month(db, tipo, ano, mes, lock=True)
    check_version(month, version, expected_id)
    before = month_payload(month)
    try:
        audit(db, month, username, "Excluiu metas", before, None)
        db.delete(month)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"mensagem": "Planejamento mensal excluído com sucesso."}
