from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from . import models, schemas
from datetime import datetime

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

def get_notas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.NotaFiscal).offset(skip).limit(limit).all()

def get_nota(db: Session, nota_id: int):
    return db.query(models.NotaFiscal).filter(models.NotaFiscal.id == nota_id).first()

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


def create_faturista(db: Session, faturista: schemas.FaturistaCreate):
    db_faturista = models.Faturista(nome=faturista.nome.strip(), ativo=True)
    db.add(db_faturista)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(db_faturista)
    return db_faturista


def get_faturistas(db: Session, incluir_inativos: bool = False):
    query = db.query(models.Faturista)
    if not incluir_inativos:
        query = query.filter(models.Faturista.ativo.is_(True))
    return query.order_by(models.Faturista.nome).all()


def get_faturista(db: Session, faturista_id: int):
    return db.query(models.Faturista).filter(models.Faturista.id == faturista_id).first()


def update_faturista(db: Session, faturista_id: int, faturista_data: schemas.FaturistaUpdate):
    faturista = get_faturista(db, faturista_id)
    if not faturista:
        return None
    faturista.nome = faturista_data.nome.strip()
    faturista.ativo = faturista_data.ativo
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(faturista)
    return faturista


def deactivate_faturista(db: Session, faturista_id: int):
    faturista = get_faturista(db, faturista_id)
    if faturista:
        faturista.ativo = False
        db.commit()
        db.refresh(faturista)
    return faturista
