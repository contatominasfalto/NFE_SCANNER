from datetime import datetime
import os
from pathlib import Path
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import barcode_service, crud, integra_api, models, report_service, schemas
from .config import REPORT_DIR
from .database import engine, ensure_schema, get_db
from .logging_config import configure_logging, mask_access_key

logger = configure_logging()
models.Base.metadata.create_all(bind=engine)
ensure_schema()

tags_metadata = [
    {
        "name": "Sistema",
        "description": "Endpoints de status e verificacao da API.",
    },
    {
        "name": "Codigo de barras",
        "description": (
            "Leitura e validacao da chave de acesso da NF-e recebida de um leitor "
            "fisico estilo supermercado. A chave validada consulta a API fiscal "
            "particular para preencher os dados da nota. Configure MEUDANFE_API_KEY "
            "somente no backend."
        ),
    },
    {
        "name": "Notas fiscais",
        "description": (
            "Cadastro e consulta das notas fiscais salvas no banco. "
            "Cada nota conferida no app e gravada individualmente com o local "
            "A1BR, A1BR/PRU ou A2BR escolhido antes da bipagem."
        ),
    },
    {
        "name": "XML",
        "description": "Geracao de arquivo XML para uma nota especifica ou para notas filtradas.",
    },
    {
        "name": "Faturistas",
        "description": "Cadastro e administracao dos faturistas disponiveis no painel operacional.",
    },
]

app = FastAPI(
    title="NFE Scanner API",
    description=(
        "API do sistema NF-e Scanner para leitura de codigo de barras, cadastro, "
        "listagem e geracao de XML das notas fiscais.\n\n"
        "Fluxo mobile atual: o operador bipa o codigo de barras da NF-e, o app chama "
        "/barcode-nf/, consulta a API fiscal particular e abre a conferencia preenchida. "
        "Antes da leitura, o operador escolhe o local A1BR, A1BR/PRU ou A2BR. "
        "Produto, peso liquido e transportador sao obtidos do XML quando disponiveis. "
        "Ao escolher 'Salvar e proxima', o app grava a nota atual no local escolhido "
        "e volta ao leitor. Ao escolher 'Salvar e finalizar', grava a nota atual e encerra o processo."
    ),
    version="0.13.1",
    openapi_tags=tags_metadata,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, error: RequestValidationError):
    logger.warning(
        "Payload invalido | metodo=%s | rota=%s | erros=%s",
        request.method,
        request.url.path,
        error.errors(),
    )
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": error.errors()}))


PANEL_DIR = Path(__file__).resolve().parents[1] / "panel"
app.mount("/painel-assets", StaticFiles(directory=PANEL_DIR), name="painel-assets")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (perf_counter() - started_at) * 1000
        logger.exception(
            "Requisicao falhou | metodo=%s | rota=%s | duracao_ms=%.1f",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (perf_counter() - started_at) * 1000
    log_method = logger.warning if response.status_code >= 400 else logger.info
    log_method(
        "Requisicao concluida | metodo=%s | rota=%s | status=%s | duracao_ms=%.1f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get(
    "/health/",
    tags=["Sistema"],
    summary="Verificar status da API",
    description="Retorna um status simples para confirmar que o backend esta online.",
)
def health_check():
    return {"status": "ok"}


@app.get("/painel", include_in_schema=False, response_class=FileResponse)
def painel():
    return FileResponse(PANEL_DIR / "index.html")


@app.get("/", include_in_schema=False, response_class=RedirectResponse)
def root():
    return RedirectResponse("/painel")


@app.post(
    "/barcode-nf/",
    response_model=schemas.BarcodeResult,
    tags=["Codigo de barras"],
    summary="Ler chave de acesso pelo codigo de barras",
    description=(
        "Recebe o texto enviado por um leitor fisico de codigo de barras, remove "
        "espacos e caracteres separadores, valida a chave de acesso da NF-e, consulta "
        "a API fiscal particular e retorna os dados da nota para conferencia.\n\n"
        "A chave valida deve conter exatamente 44 digitos. A credencial da API "
        "fiscal deve ser configurada em MEUDANFE_API_KEY no backend."
    ),
    responses={
        400: {"description": "Codigo de barras sem uma chave NF-e valida de 44 digitos."},
        404: {"description": "Nota fiscal nao encontrada na API fiscal."},
        502: {"description": "Falha ao consultar ou interpretar a resposta da API fiscal."},
        503: {"description": "Integracao fiscal indisponivel ou nao configurada."},
    },
)
def read_barcode(barcode_data: schemas.BarcodeInput):
    try:
        chave_acesso = barcode_service.extract_access_key(barcode_data.codigo_barras)
    except ValueError as error:
        logger.warning("Codigo de barras invalido | motivo=%s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        nota = integra_api.consultar_nfe(chave_acesso)
    except integra_api.IntegracaoAPIError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error

    logger.info("Leitura concluida | chave=%s | numero=%s", mask_access_key(chave_acesso), nota["numero_nf"])
    return schemas.BarcodeResult(
        chave_acesso=chave_acesso,
        quantidade_digitos=len(chave_acesso),
        nota=nota,
    )


@app.post(
    "/notas/importar-barcode/",
    response_model=schemas.NotaFiscalResponse,
    tags=["Notas fiscais"],
    summary="Consultar e cadastrar nota pela chave",
    description=(
        "Executa o fluxo completo para testes pelo Swagger: valida o codigo de barras, "
        "consulta a API fiscal particular e salva os dados retornados no banco com o "
        "local informado.\n\n"
        "No aplicativo mobile, o fluxo permanece em duas etapas para permitir que o "
        "operador confira os dados antes de salvar."
    ),
    responses={
        400: {"description": "Codigo de barras sem uma chave NF-e valida de 44 digitos."},
        404: {"description": "Nota fiscal nao encontrada na API fiscal."},
        409: {"description": "Nota fiscal ja cadastrada."},
        502: {"description": "Falha ao consultar ou interpretar a resposta da API fiscal."},
        503: {"description": "Integracao fiscal indisponivel ou nao configurada."},
    },
)
def importar_barcode(barcode_data: schemas.BarcodeImportInput, db: Session = Depends(get_db)):
    barcode_result = read_barcode(barcode_data)
    nota_data = schemas.NotaFiscalCreate(
        **barcode_result.nota.model_dump(exclude={"local"}),
        local=barcode_data.local,
    )

    try:
        nota = crud.create_nota(db, nota_data)
    except IntegrityError as error:
        logger.warning("Importacao duplicada | chave=%s", mask_access_key(nota_data.chave_acesso))
        raise HTTPException(status_code=409, detail="Nota fiscal ja cadastrada para esta chave de acesso.") from error
    logger.info("Nota importada | id=%s | numero=%s | local=%s", nota.id, nota.numero_nf, nota.local)
    return nota


@app.post(
    "/notas/",
    response_model=schemas.NotaFiscalResponse,
    tags=["Notas fiscais"],
    summary="Cadastrar nota fiscal",
    description=(
        "Grava no banco uma nota fiscal ja conferida pelo usuario no aplicativo. "
        "O local e obrigatorio e aceita A1BR, A1BR/PRU ou A2BR. "
        "Nos lancamentos feitos pelo app, faturista deve ser BIPE. "
        "No fluxo principal, use este endpoint depois da leitura por /barcode-nf/ "
        "e da confirmacao manual dos dados.\n\n"
        "No botao 'Salvar e proxima', o app chama este endpoint para gravar a nota "
        "atual e depois volta ao leitor. No botao 'Salvar e finalizar', "
        "tambem chama este endpoint e encerra o fluxo."
    ),
)
def create_nota(nota_data: schemas.NotaFiscalCreate, db: Session = Depends(get_db)):
    try:
        nota = crud.create_nota(db, nota_data, nota_data.caminho_arquivo_imagem)
    except IntegrityError as error:
        logger.warning("Cadastro duplicado | chave=%s", mask_access_key(nota_data.chave_acesso))
        raise HTTPException(status_code=409, detail="Nota fiscal ja cadastrada para esta chave de acesso.") from error
    logger.info("Nota cadastrada | id=%s | numero=%s | local=%s", nota.id, nota.numero_nf, nota.local)
    return nota


@app.get(
    "/notas/",
    response_model=list[schemas.NotaFiscalResponse],
    tags=["Notas fiscais"],
    summary="Listar notas fiscais cadastradas",
    description=(
        "Retorna as notas fiscais salvas no banco. O aplicativo usa este endpoint "
        "para preencher a tela Notas escaneadas. Registros antigos podem retornar "
        "local vazio."
    ),
)
def list_notas(
    skip: int = Query(0, ge=0, description="Quantidade de registros a ignorar."),
    limit: int = Query(100, ge=1, le=500, description="Quantidade maxima de notas retornadas."),
    db: Session = Depends(get_db),
):
    return crud.get_notas(db, skip=skip, limit=limit)


@app.put(
    "/notas/{nota_id}/",
    response_model=schemas.NotaFiscalResponse,
    tags=["Notas fiscais"],
    summary="Editar nota fiscal",
    description=(
        "Atualiza os dados de uma nota fiscal cadastrada pelo ID. "
        "O local tambem pode ser atualizado. "
        "O aplicativo usa este endpoint quando o operador edita uma nota "
        "pela tela Detalhes da nota."
    ),
    responses={
        404: {"description": "Nota fiscal nao encontrada."},
        409: {"description": "A chave de acesso informada ja pertence a outra nota."},
    },
)
def update_nota(nota_id: int, nota_data: schemas.NotaFiscalUpdate, db: Session = Depends(get_db)):
    try:
        nota = crud.update_nota(db, nota_id, nota_data)
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="Ja existe uma nota fiscal cadastrada para esta chave de acesso.") from error

    if not nota:
        logger.warning("Edicao recusada: nota nao encontrada | id=%s", nota_id)
        raise HTTPException(status_code=404, detail="Nota fiscal nao encontrada.")
    logger.info("Nota atualizada | id=%s | numero=%s | local=%s", nota.id, nota.numero_nf, nota.local)
    return nota


@app.delete(
    "/notas/{nota_id}/",
    response_model=schemas.NotaFiscalDeleteResponse,
    tags=["Notas fiscais"],
    summary="Excluir nota fiscal",
    description=(
        "Exclui uma nota fiscal cadastrada pelo ID. Use este endpoint no Swagger "
        "para remover uma massa de teste e repetir a importacao da mesma chave."
    ),
    responses={
        404: {"description": "Nota fiscal nao encontrada."},
    },
)
def delete_nota(nota_id: int, db: Session = Depends(get_db)):
    nota = crud.delete_nota(db, nota_id)
    if not nota:
        logger.warning("Exclusao recusada: nota nao encontrada | id=%s", nota_id)
        raise HTTPException(status_code=404, detail="Nota fiscal nao encontrada.")

    logger.info("Nota excluida | id=%s | numero=%s", nota.id, nota.numero_nf)
    return schemas.NotaFiscalDeleteResponse(
        id=nota.id,
        numero_nf=nota.numero_nf,
        chave_acesso=nota.chave_acesso,
        mensagem="Nota fiscal excluida com sucesso.",
    )


@app.post(
    "/faturistas/",
    response_model=schemas.FaturistaResponse,
    tags=["Faturistas"],
    summary="Cadastrar faturista",
    responses={409: {"description": "Faturista ja cadastrado."}},
)
def create_faturista(faturista_data: schemas.FaturistaCreate, db: Session = Depends(get_db)):
    try:
        faturista = crud.create_faturista(db, faturista_data)
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="Faturista ja cadastrado.") from error
    logger.info("Faturista cadastrado | id=%s | nome=%s", faturista.id, faturista.nome)
    return faturista


@app.get(
    "/faturistas/",
    response_model=list[schemas.FaturistaResponse],
    tags=["Faturistas"],
    summary="Listar faturistas",
)
def list_faturistas(
    incluir_inativos: bool = Query(False, description="Inclui faturistas desativados."),
    db: Session = Depends(get_db),
):
    return crud.get_faturistas(db, incluir_inativos)


@app.put(
    "/faturistas/{faturista_id}/",
    response_model=schemas.FaturistaResponse,
    tags=["Faturistas"],
    summary="Editar faturista",
    responses={404: {"description": "Faturista nao encontrado."}, 409: {"description": "Nome ja cadastrado."}},
)
def update_faturista(
    faturista_id: int,
    faturista_data: schemas.FaturistaUpdate,
    db: Session = Depends(get_db),
):
    atual = crud.get_faturista(db, faturista_id)
    if not atual:
        raise HTTPException(status_code=404, detail="Faturista nao encontrado.")
    if atual.nome == "BIPE" and (faturista_data.nome != "BIPE" or not faturista_data.ativo):
        raise HTTPException(status_code=409, detail="O faturista padrao BIPE nao pode ser renomeado ou desativado.")
    try:
        faturista = crud.update_faturista(db, faturista_id, faturista_data)
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="Ja existe um faturista com este nome.") from error
    logger.info("Faturista atualizado | id=%s | nome=%s | ativo=%s", faturista.id, faturista.nome, faturista.ativo)
    return faturista


@app.delete(
    "/faturistas/{faturista_id}/",
    response_model=schemas.FaturistaDeleteResponse,
    tags=["Faturistas"],
    summary="Desativar faturista",
    responses={404: {"description": "Faturista nao encontrado."}, 409: {"description": "BIPE nao pode ser desativado."}},
)
def delete_faturista(faturista_id: int, db: Session = Depends(get_db)):
    atual = crud.get_faturista(db, faturista_id)
    if not atual:
        raise HTTPException(status_code=404, detail="Faturista nao encontrado.")
    if atual.nome == "BIPE":
        raise HTTPException(status_code=409, detail="O faturista padrao BIPE nao pode ser desativado.")
    faturista = crud.deactivate_faturista(db, faturista_id)
    logger.info("Faturista desativado | id=%s | nome=%s", faturista.id, faturista.nome)
    return schemas.FaturistaDeleteResponse(
        id=faturista.id,
        nome=faturista.nome,
        mensagem="Faturista desativado com sucesso.",
    )


@app.post(
    "/relatorio/",
    response_class=FileResponse,
    tags=["XML"],
    summary="Gerar XML de nota fiscal",
    description=(
        "Gera um arquivo XML. Para o fluxo atual do app, informe nota_id para gerar "
        "o XML de uma unica nota a partir da tela Detalhes da nota. Sem nota_id, "
        "a API gera um XML com todas as notas que atenderem aos filtros opcionais."
    ),
    responses={
        200: {
            "description": "Arquivo XML gerado com sucesso.",
            "content": {"application/xml": {"example": "<?xml version='1.0' encoding='utf-8'?><relatorio_notas_fiscais />"}},
        },
        400: {"description": "Formato invalido ou parametros invalidos."},
        404: {"description": "Nenhuma nota encontrada com os filtros informados."},
    },
)
def gerar_relatorio(
    nota_id: int | None = Query(
        None,
        ge=1,
        description="ID da nota fiscal. Quando informado, gera XML apenas desta nota.",
    ),
    data_inicio: str | None = Query(
        None,
        description="Data inicial do filtro no formato YYYY-MM-DD. Usado apenas quando nota_id nao for informado.",
        examples=["2026-05-01"],
    ),
    data_fim: str | None = Query(
        None,
        description="Data final do filtro no formato YYYY-MM-DD. Usado apenas quando nota_id nao for informado.",
        examples=["2026-05-31"],
    ),
    fornecedor: str | None = Query(
        None,
        description="Trecho do nome do fornecedor para filtrar notas. Usado apenas quando nota_id nao for informado.",
    ),
    valor_min: float | None = Query(
        None,
        ge=0,
        description="Valor minimo da nota. Usado apenas quando nota_id nao for informado.",
    ),
    valor_max: float | None = Query(
        None,
        ge=0,
        description="Valor maximo da nota. Usado apenas quando nota_id nao for informado.",
    ),
    formato: str = Query(
        "xml",
        pattern="^xml$",
        description="Formato do arquivo gerado. Atualmente apenas xml e suportado.",
    ),
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
        nota_id,
    )

    if not notas:
        raise HTTPException(status_code=404, detail="Nenhuma nota encontrada com os filtros")

    if formato != "xml":
        raise HTTPException(status_code=400, detail="Formato inválido. Use apenas xml.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nota_fiscal_{nota_id}_{timestamp}.xml" if nota_id else f"notas_fiscais_{timestamp}.xml"
    filepath = os.path.join(REPORT_DIR, filename)

    if nota_id:
        filtros_str = f"Nota ID: {nota_id}"
    else:
        filtros_str = (
            f"Periodo: {data_inicio or 'inicio'} a {data_fim or 'fim'} | "
            f"Fornecedor: {fornecedor or 'todos'} | "
            f"Valor minimo: {valor_min if valor_min is not None else 'todos'} | "
            f"Valor maximo: {valor_max if valor_max is not None else 'todos'}"
        )

    report_service.generate_xml(notas, filtros_str, filepath)
    logger.info("XML gerado | nota_id=%s | quantidade=%s | arquivo=%s", nota_id, len(notas), filename)

    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/xml",
    )
