from datetime import datetime
import os
import shutil

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import crud, models, ocr_service, report_service, schemas
from .config import REPORT_DIR, UPLOAD_DIR
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NFE Scanner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def save_upload_file(file: UploadFile) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = os.path.basename(file.filename or "nota.jpg")
    filename = f"{timestamp}_{safe_name}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return filepath


@app.get("/health/")
def health_check():
    return {"status": "ok"}


@app.post("/ocr-nf/", response_model=schemas.OCRResult)
async def ocr_nf(file: UploadFile = File(...)):
    filepath = save_upload_file(file)
    ocr_data = ocr_service.extract_nfe_data(filepath)
    return schemas.OCRResult(**ocr_data, caminho_arquivo_imagem=filepath)


@app.post("/notas/", response_model=schemas.NotaFiscalResponse)
def create_nota(nota_data: schemas.NotaFiscalCreate, db: Session = Depends(get_db)):
    return crud.create_nota(db, nota_data, nota_data.caminho_arquivo_imagem)


@app.post("/upload-nf/", response_model=schemas.NotaFiscalResponse)
async def upload_nf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = save_upload_file(file)
    ocr_data = ocr_service.extract_nfe_data(filepath)
    nota_data = schemas.NotaFiscalCreate(**ocr_data, caminho_arquivo_imagem=filepath)
    return crud.create_nota(db, nota_data, filepath)


@app.get("/notas/", response_model=list[schemas.NotaFiscalResponse])
def list_notas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_notas(db, skip=skip, limit=limit)


@app.post("/relatorio/")
def gerar_relatorio(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    fornecedor: str | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    formato: str = "xml",
    db: Session = Depends(get_db),
):
    data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d") if data_inicio else None
    data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d") if data_fim else None

    notas = crud.filter_notas(
        db,
        data_inicio_dt,
        data_fim_dt,
        fornecedor,
        valor_min,
        valor_max,
    )

    if not notas:
        raise HTTPException(status_code=404, detail="Nenhuma nota encontrada com os filtros")

    if formato != "xml":
        raise HTTPException(status_code=400, detail="Formato inválido. Use apenas xml.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"notas_fiscais_{timestamp}.xml"
    filepath = os.path.join(REPORT_DIR, filename)

    filtros_str = (
        f"Periodo: {data_inicio or 'inicio'} a {data_fim or 'fim'} | "
        f"Fornecedor: {fornecedor or 'todos'} | "
        f"Valor minimo: {valor_min if valor_min is not None else 'todos'} | "
        f"Valor maximo: {valor_max if valor_max is not None else 'todos'}"
    )

    report_service.generate_xml(notas, filtros_str, filepath)

    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/xml",
    )