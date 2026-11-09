"""Rotas do módulo Meta. A autenticação é injetada pela aplicação."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.orm import Session

from .access_control import has_access
from .database import get_db
from .metas_models import MetaMes
from .metas_schemas import MetaMesInput, MetaMesResponse, MetaMesSummary, MetaMesUpdate, MetaTipo
from .metas_service import delete_month, find_month, month_payload, save_month, summary


Ano = Annotated[int, Path(ge=2000, le=2100)]
Mes = Annotated[int, Path(ge=1, le=12)]


def create_metas_router(authenticate):
    router = APIRouter(prefix="/metas", tags=["Metas"])

    def permitted_user(request: Request, user=Depends(authenticate)):
        action = "view" if request.method == "GET" else "operate"
        if not has_access(user, "metas", action):
            raise HTTPException(403, "Usuário sem permissão para esta operação no módulo Metas.")
        return user

    @router.get("/{tipo}/meses/", response_model=list[MetaMesSummary])
    def list_months(tipo: MetaTipo, user=Depends(permitted_user), db: Session = Depends(get_db)):
        months = db.query(MetaMes).filter_by(tipo=tipo).order_by(MetaMes.ano.desc(), MetaMes.mes.desc()).all()
        return [summary(month) for month in months]

    @router.get("/{tipo}/{ano}/{mes}/", response_model=MetaMesResponse)
    def get_month(tipo: MetaTipo, ano: Ano, mes: Mes, user=Depends(permitted_user), db: Session = Depends(get_db)):
        return month_payload(find_month(db, tipo, ano, mes))

    @router.post("/{tipo}/", response_model=MetaMesResponse, status_code=201)
    def create_month(tipo: MetaTipo, payload: MetaMesInput, user=Depends(permitted_user), db: Session = Depends(get_db)):
        return save_month(db, tipo, payload, user.username)

    @router.put("/{tipo}/{ano}/{mes}/", response_model=MetaMesResponse)
    def update_month(tipo: MetaTipo, ano: Ano, mes: Mes, payload: MetaMesUpdate, user=Depends(permitted_user), db: Session = Depends(get_db)):
        if (ano, mes) != (payload.ano, payload.mes):
            raise HTTPException(422, "O período informado deve ser igual ao mês selecionado.")
        return save_month(db, tipo, payload, user.username, editing=True)

    @router.delete("/{tipo}/{ano}/{mes}/")
    def remove_month(tipo: MetaTipo, ano: Ano, mes: Mes, versao: Annotated[int, Query(ge=1)], id: Annotated[int, Query(ge=1)], user=Depends(permitted_user), db: Session = Depends(get_db)):
        return delete_month(db, tipo, ano, mes, versao, id, user.username)

    return router
