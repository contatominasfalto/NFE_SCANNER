import hashlib
import hmac
import os
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
    username = faturista.nome.strip()
    return create_user(db, username, faturista.senha, role="user", active=True)


def get_faturistas(db: Session, incluir_inativos: bool = False):
    query = db.query(models.User).filter(models.User.role == "user")
    if not incluir_inativos:
        query = query.filter(models.User.active.is_(True))
    return query.order_by(models.User.username).all()


def get_faturista(db: Session, faturista_id: int):
    return db.query(models.User).filter(models.User.id == faturista_id, models.User.role == "user").first()


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


def deactivate_faturista(db: Session, faturista_id: int):
    faturista = get_faturista(db, faturista_id)
    if faturista:
        faturista.active = False
        db.commit()
        db.refresh(faturista)
    return faturista
