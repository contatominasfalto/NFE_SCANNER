from sqlalchemy.orm import Session
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
    db.commit()
    db.refresh(db_nota)
    return db_nota

def get_notas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.NotaFiscal).offset(skip).limit(limit).all()

def filter_notas(db: Session, data_inicio=None, data_fim=None, fornecedor=None, valor_min=None, valor_max=None):
    query = db.query(models.NotaFiscal)
    
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
