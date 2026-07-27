import hashlib
import hmac
import os
from collections import defaultdict
from sqlalchemy import case, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from . import models, schemas
from datetime import datetime, timedelta

def _nota_sem_erro():
    return or_(
        models.NotaFiscal.erro_salvamento.is_(False),
        models.NotaFiscal.erro_salvamento.is_(None),
    )

def _nota_no_periodo(inicio: datetime, fim: datetime):
    return or_(
        models.NotaFiscal.data_emissao.between(inicio, fim),
        models.NotaFiscal.data_cadastro.between(inicio, fim),
    )

def _data_referencia_periodo(nota: models.NotaFiscal, inicio: datetime, fim: datetime):
    if nota.data_emissao and inicio <= nota.data_emissao <= fim:
        return nota.data_emissao
    if nota.data_cadastro and inicio <= nota.data_cadastro <= fim:
        return nota.data_cadastro
    return nota.data_emissao or nota.data_cadastro

def create_nota(db: Session, nota: schemas.NotaFiscalCreate, imagem_path: str | None = None):
    data = nota.model_dump()
    data.pop("caminho_arquivo_imagem", None)
    db_nota = models.NotaFiscal(
        **data,
        caminho_arquivo_imagem=imagem_path or nota.caminho_arquivo_imagem,
        data_cadastro=datetime.now()
    )
    db.add(db_nota)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(db_nota)
    return db_nota


def create_nota_erro(db: Session, erro: schemas.NotaFiscalErrorCreate):
    db_nota = models.NotaFiscal(
        numero_nf="ERRO",
        serie="ERRO",
        data_emissao=datetime.now(),
        cnpj_fornecedor="ERRO",
        nome_fornecedor="ERRO",
        valor_total=0,
        chave_acesso=erro.chave_acesso.strip(),
        local=erro.local if erro.local in {local.value for local in schemas.Local} else None,
        produto="ERRO",
        quantidade=None,
        transportador="ERRO",
        faturista=erro.faturista or "BIPE",
        lider_operacional="ERRO",
        observacao="ERRO",
        erro_salvamento=True,
        erro_detalhe=erro.detalhe,
        data_cadastro=datetime.now(),
    )
    db.add(db_nota)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(db_nota)
    return db_nota

def get_notas(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    data_cadastro_inicio: datetime | None = None,
    data_cadastro_fim: datetime | None = None,
):
    query = db.query(models.NotaFiscal)
    if data_cadastro_inicio:
        query = query.filter(models.NotaFiscal.data_cadastro >= data_cadastro_inicio)
    if data_cadastro_fim:
        query = query.filter(models.NotaFiscal.data_cadastro <= data_cadastro_fim)
    return (
        query.order_by(models.NotaFiscal.data_cadastro.desc(), models.NotaFiscal.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_nota(db: Session, nota_id: int):
    return db.query(models.NotaFiscal).filter(models.NotaFiscal.id == nota_id).first()


def get_notas_erro(db: Session):
    return (
        db.query(models.NotaFiscal)
        .filter(models.NotaFiscal.produto.ilike("%ERRO%"))
        .order_by(models.NotaFiscal.id)
        .all()
    )


def corrigir_fuso_emissao_suspeito(db: Session, horas: int = 3):
    notas = (
        db.query(models.NotaFiscal)
        .filter(
            models.NotaFiscal.data_emissao.isnot(None),
            _nota_sem_erro(),
        )
        .order_by(models.NotaFiscal.id)
        .all()
    )
    deslocamento = timedelta(hours=horas)
    corrigidas = []

    for nota in notas:
        data_emissao = nota.data_emissao
        if not data_emissao or data_emissao.hour >= horas:
            continue

        antes = data_emissao
        depois = antes - deslocamento
        nota.data_emissao = depois
        corrigidas.append(
            {
                "id": nota.id,
                "chave_acesso": nota.chave_acesso,
                "numero_nf": nota.numero_nf,
                "antes": antes,
                "depois": depois,
            }
        )

    if corrigidas:
        db.commit()

    return corrigidas


def resolve_nota_erro(db: Session, nota: models.NotaFiscal, nota_data: dict):
    local_original = nota.local
    for field, value in nota_data.items():
        if hasattr(nota, field) and field not in {"id", "local", "data_cadastro"}:
            setattr(nota, field, value)
    nota.local = local_original
    nota.faturista = nota_data.get("faturista") or "BIPE"
    nota.lider_operacional = None
    nota.caminho_arquivo_imagem = None
    nota.erro_salvamento = False
    nota.erro_detalhe = None
    db.commit()
    db.refresh(nota)
    return nota


def update_nota_erro_detalhe(db: Session, nota: models.NotaFiscal, detalhe: str):
    nota.erro_detalhe = detalhe[:2000]
    db.commit()
    db.refresh(nota)
    return nota


def refresh_nota_from_api_data(db: Session, nota: models.NotaFiscal, nota_data: dict):
    local_original = nota.local
    faturista_original = nota.faturista
    data_cadastro_original = nota.data_cadastro

    for field, value in nota_data.items():
        if hasattr(nota, field) and field not in {"id", "local", "data_cadastro"}:
            setattr(nota, field, value)

    nota.local = local_original
    nota.faturista = faturista_original or nota_data.get("faturista") or "BIPE"
    nota.data_cadastro = data_cadastro_original
    nota.erro_salvamento = False
    nota.erro_detalhe = None

    db.commit()
    db.refresh(nota)
    return nota


def update_nota(db: Session, nota_id: int, nota_data: schemas.NotaFiscalUpdate):
    nota = get_nota(db, nota_id)
    if not nota:
        return None

    for field, value in nota_data.model_dump().items():
        setattr(nota, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(nota)
    return nota

def delete_nota(db: Session, nota_id: int):
    nota = get_nota(db, nota_id)
    if nota:
        db.delete(nota)
        db.commit()
    return nota

def create_audit_log(
    db: Session,
    usuario: str,
    acao: str,
    area: str,
    descricao: str,
    entidade: str | None = None,
    entidade_id: str | int | None = None,
    detalhes: str | None = None,
):
    log = models.AuditLog(
        usuario=usuario,
        acao=acao,
        area=area,
        entidade=entidade,
        entidade_id=str(entidade_id) if entidade_id is not None else None,
        descricao=descricao,
        detalhes=detalhes,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def list_audit_logs(db: Session, skip: int = 0, limit: int = 200):
    return (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.created_at.desc(), models.AuditLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def filter_notas(db: Session, data_inicio=None, data_fim=None, fornecedor=None, valor_min=None, valor_max=None, nota_id=None):
    query = db.query(models.NotaFiscal)
    
    if nota_id is not None:
        query = query.filter(models.NotaFiscal.id == nota_id)
    if data_inicio:
        query = query.filter(models.NotaFiscal.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(models.NotaFiscal.data_emissao <= data_fim)
    if fornecedor:
        query = query.filter(models.NotaFiscal.nome_fornecedor.contains(fornecedor))
    if valor_min is not None:
        query = query.filter(models.NotaFiscal.valor_total >= valor_min)
    if valor_max is not None:
        query = query.filter(models.NotaFiscal.valor_total <= valor_max)
    
    return query.all()


def get_relatorio_operacional(
    db: Session,
    inicio_mes: datetime,
    fim_mes: datetime,
    inicio_dia: datetime,
    fim_dia: datetime,
    material: str | None = None,
):
    material_normalizado = material.strip() if material else None
    notas = (
        db.query(models.NotaFiscal)
        .filter(
            _nota_no_periodo(inicio_mes, fim_mes),
            _nota_sem_erro(),
        )
        .all()
    )

    def resumir(inicio: datetime, fim: datetime):
        produtos = defaultdict(float)
        total_quantidade = 0.0
        total_notas = 0

        for nota in notas:
            data_referencia = _data_referencia_periodo(nota, inicio, fim)
            if not data_referencia or data_referencia < inicio or data_referencia > fim:
                continue
            quantidade = float(nota.quantidade or 0)
            produto = (nota.produto or "Sem produto").strip() or "Sem produto"
            if material_normalizado and produto != material_normalizado:
                continue
            produtos[produto] += quantidade
            total_quantidade += quantidade
            total_notas += 1

        return {
            "inicio": inicio,
            "fim": fim,
            "total_ton": round(total_quantidade / 1000, 3),
            "total_notas": total_notas,
            "produtos": [
                {"produto": produto, "quantidade_ton": round(quantidade / 1000, 3)}
                for produto, quantidade in sorted(produtos.items(), key=lambda item: item[1], reverse=True)
            ],
        }

    return {"mes": resumir(inicio_mes, fim_mes), "dia": resumir(inicio_dia, fim_dia)}


def get_relatorio_material(db: Session, inicio: datetime, fim: datetime, material: str | None = None):
    notas = (
        db.query(models.NotaFiscal)
        .filter(
            _nota_no_periodo(inicio, fim),
            _nota_sem_erro(),
        )
        .all()
    )
    materiais = defaultdict(lambda: {"quantidade": 0.0, "nfes": 0})
    material_normalizado = material.strip() if material else None

    for nota in notas:
        material = (nota.produto or "Sem produto").strip() or "Sem produto"
        if material_normalizado and material != material_normalizado:
            continue
        materiais[material]["quantidade"] += float(nota.quantidade or 0)
        materiais[material]["nfes"] += 1

    itens = [
        {
            "material": material,
            "quantidade_ton": round(dados["quantidade"] / 1000, 3),
            "quantidade_nfes": dados["nfes"],
        }
        for material, dados in sorted(
            materiais.items(),
            key=lambda item: item[1]["quantidade"],
            reverse=True,
        )
    ]
    return {
        "inicio": inicio,
        "fim": fim,
        "total_ton": round(sum(dados["quantidade"] for dados in materiais.values()) / 1000, 3),
        "total_nfes": sum(dados["nfes"] for dados in materiais.values()),
        "materiais": itens,
    }


def get_relatorio_material_local(db: Session, inicio: datetime, fim: datetime, material: str | None = None):
    notas = (
        db.query(models.NotaFiscal)
        .filter(
            _nota_no_periodo(inicio, fim),
            _nota_sem_erro(),
        )
        .all()
    )
    materiais = defaultdict(
        lambda: {
            "CDMA": {"quantidade": 0.0, "nfes": 0},
            "PRU": {"quantidade": 0.0, "nfes": 0},
        }
    )
    material_normalizado = material.strip() if material else None

    for nota in notas:
        material = (nota.produto or "Sem produto").strip() or "Sem produto"
        if material_normalizado and material != material_normalizado:
            continue
        local = nota.local if nota.local in {"CDMA", "PRU"} else None
        if not local:
            continue
        materiais[material][local]["quantidade"] += float(nota.quantidade or 0)
        materiais[material][local]["nfes"] += 1

    return {
        "inicio": inicio,
        "fim": fim,
        "materiais": [
            {
                "material": material,
                "quantidade_cdma_ton": round(dados["CDMA"]["quantidade"] / 1000, 3),
                "quantidade_nfes_cdma": dados["CDMA"]["nfes"],
                "quantidade_pru_ton": round(dados["PRU"]["quantidade"] / 1000, 3),
                "quantidade_nfes_pru": dados["PRU"]["nfes"],
            }
            for material, dados in sorted(
                materiais.items(),
                key=lambda item: item[1]["CDMA"]["quantidade"] + item[1]["PRU"]["quantidade"],
                reverse=True,
            )
        ],
    }


def get_relatorio_recebimento(db: Session, inicio: datetime, fim: datetime, material: str | None = None):
    query = db.query(models.NotaFiscal).filter(
        _nota_no_periodo(inicio, fim),
        _nota_sem_erro(),
    )
    notas_periodo = query.all()
    materiais_disponiveis = sorted(
        {
            (nota.produto or "Sem produto").strip() or "Sem produto"
            for nota in notas_periodo
        },
        key=str.casefold,
    )
    material_normalizado = material.strip() if material else None
    dias = defaultdict(lambda: defaultdict(float))
    totais_materiais = defaultdict(float)

    for nota in notas_periodo:
        produto = (nota.produto or "Sem produto").strip() or "Sem produto"
        if material_normalizado and produto != material_normalizado:
            continue
        quantidade = float(nota.quantidade or 0)
        data_referencia = _data_referencia_periodo(nota, inicio, fim)
        if not data_referencia:
            continue
        dias[data_referencia.date().isoformat()][produto] += quantidade
        totais_materiais[produto] += quantidade

    itens = []
    data_atual = inicio.date()
    while data_atual <= fim.date():
        valores = dias[data_atual.isoformat()]
        itens.append(
            {
                "data": data_atual.isoformat(),
                "materiais_ton": {
                    produto: round(quantidade / 1000, 3)
                    for produto, quantidade in sorted(valores.items())
                },
            }
        )
        data_atual += timedelta(days=1)
    totais = [
        {"material": produto, "total_ton": round(quantidade / 1000, 3)}
        for produto, quantidade in sorted(totais_materiais.items(), key=lambda item: item[1], reverse=True)
    ]
    return {
        "inicio": inicio,
        "fim": fim,
        "material": material_normalizado,
        "materiais_disponiveis": materiais_disponiveis,
        "totais_materiais": totais,
        "total_ton": round(sum(item["total_ton"] for item in totais), 3),
        "dias": itens,
    }


def create_faturista(db: Session, faturista: schemas.FaturistaCreate):
    username = faturista.nome.strip()
    return create_user(db, username, faturista.senha, role="user", active=True)


def get_faturistas(db: Session, incluir_inativos: bool = False):
    query = db.query(models.User).filter(models.User.role.in_(("user", "viewer")))
    if not incluir_inativos:
        query = query.filter(models.User.active.is_(True))
    fixed_user_order = case(
        (models.User.username == "BIPE", 0),
        (models.User.username == "viewer_user", 1),
        else_=2,
    )
    return query.order_by(fixed_user_order, models.User.username).all()


def get_faturista(db: Session, faturista_id: int):
    return db.query(models.User).filter(
        models.User.id == faturista_id,
        models.User.role.in_(("user", "viewer")),
    ).first()


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return password_hash.hex(), salt.hex()


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    computed_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100000).hex()
    return hmac.compare_digest(password_hash, computed_hash)


def create_user(db: Session, username: str, password: str, role: str = "user", active: bool = True):
    username = username.strip()
    password_hash, salt = hash_password(password)
    db_user = models.User(
        username=username,
        password_hash=password_hash,
        salt=salt,
        role=role,
        active=active,
    )
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(db_user)
    return db_user


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username.strip()).first()


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user or not user.active:
        return None
    if not verify_password(password, user.password_hash, user.salt):
        return None
    return user


def update_faturista(db: Session, faturista_id: int, faturista_data: schemas.FaturistaUpdate):
    faturista = get_faturista(db, faturista_id)
    if not faturista:
        return None
    faturista.username = faturista_data.nome.strip()
    faturista.active = faturista_data.ativo
    if faturista_data.senha:
        password_hash, salt = hash_password(faturista_data.senha)
        faturista.password_hash = password_hash
        faturista.salt = salt
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(faturista)
    return faturista


def delete_faturista(db: Session, faturista_id: int):
    faturista = get_faturista(db, faturista_id)
    if faturista:
        db.delete(faturista)
        db.commit()
    return faturista
