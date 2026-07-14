from datetime import datetime
from calendar import monthrange
import base64
import hashlib
import hmac
from io import BytesIO
import re
import time
from pathlib import Path
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, Security
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.security import APIKeyCookie
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import barcode_service, crud, integra_api, models, report_service, schemas, config
from .database import engine, ensure_schema, get_db, SessionLocal
from .logging_config import configure_logging, mask_access_key

logger = configure_logging()
models.Base.metadata.create_all(bind=engine)
ensure_schema()

VIEWER_USERNAME = "viewer_user"
VIEWER_ROLE = "viewer"


def initialize_default_users():
    with SessionLocal() as db:
        defaults = [
            ("adm", "t@pfacil", "admin"),
            ("BIPE", "BIPE", "user"),
            ("faturista01", "faturista01", "user"),
            ("faturista02", "faturista02", "user"),
            (VIEWER_USERNAME, VIEWER_USERNAME, VIEWER_ROLE),
        ]
        for username, password, role in defaults:
            user = crud.get_user_by_username(db, username)
            if not user:
                try:
                    crud.create_user(db, username, password, role=role)
                except Exception:
                    pass
            elif user.role != role:
                user.role = role
                db.commit()

initialize_default_users()

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
            "CDMA ou PRU escolhido antes da bipagem."
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
        "Antes da leitura, o operador escolhe o local CDMA ou PRU. "
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

# Expose cookie-based session in OpenAPI (Swagger) so the panel can authorize via cookie
api_key_cookie = APIKeyCookie(name="session", auto_error=False)


def create_session_token(username: str, expires_in: int = 8 * 3600) -> str:
    expires = str(int(time.time()) + expires_in)
    payload = f"{username}|{expires}"
    signature = hmac.new(config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{signature}".encode()).decode()


def decode_session_token(token: str) -> dict[str, str] | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        username, expires, signature = raw.split("|")
        expected = hmac.new(config.SECRET_KEY.encode(), f"{username}|{expires}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        if int(expires) < int(time.time()):
            return None
        return {"username": username}
    except Exception:
        return None


def get_current_user(request: Request, db: Session = Depends(get_db), session_token: str | None = Security(api_key_cookie)):
    # Prefer explicit Security-injected cookie (so OpenAPI shows the cookie scheme),
    # but fallback to existing cookie/header behavior if not provided by the docs/ui.
    token = session_token or request.cookies.get("session") or (request.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Autenticacao exigida.")

    session_data = decode_session_token(token)
    if not session_data:
        raise HTTPException(status_code=401, detail="Sessao invalida ou expirada.")

    user = crud.get_user_by_username(db, session_data["username"])
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="Usuario invalido.")
    return user


def ensure_admin(user: models.User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito ao usuario administrador.")


def ensure_not_viewer(user: models.User):
    if user.role == VIEWER_ROLE:
        raise HTTPException(status_code=403, detail="Usuario de visualizacao nao possui acesso a esta operacao.")


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
PROJECT_DIR = Path(__file__).resolve().parents[2]
APK_DIR = PROJECT_DIR / "mobile" / "bin"
app.mount("/painel-assets", StaticFiles(directory=PANEL_DIR), name="painel-assets")


def parse_apk_version(path: Path) -> tuple[int, ...]:
    match = re.search(r"nfescanner-(\d+(?:\.\d+)*)-", path.name)
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def get_latest_apk_path() -> Path | None:
    apks = sorted(
        APK_DIR.glob("nfescanner-*-arm64-v8a-debug.apk"),
        key=lambda path: (parse_apk_version(path), path.stat().st_mtime),
        reverse=True,
    )
    return apks[0] if apks else None

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Restrict access to API docs/openapi to admin users only
    docs_paths = {"/docs", "/redoc", app.openapi_url, "/docs/oauth2-redirect"}
    if request.url.path in docs_paths:
        token = request.cookies.get("session") or (request.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Autenticacao exigida."})
        session_data = decode_session_token(token)
        if not session_data:
            return JSONResponse(status_code=401, content={"detail": "Sessao invalida ou expirada."})
        with SessionLocal() as db:
            user = crud.get_user_by_username(db, session_data["username"])
            if not user or not user.active or user.role != "admin":
                return JSONResponse(status_code=403, content={"detail": "Acesso restrito ao usuario administrador."})
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


@app.get("/app-download", include_in_schema=False, response_class=FileResponse)
def app_download():
    apk_path = get_latest_apk_path()
    if not apk_path:
        raise HTTPException(status_code=404, detail="APK nao encontrado. Gere o APK antes de baixar.")
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename=apk_path.name,
        headers={"Cache-Control": "no-store"},
    )


@app.get("/app", include_in_schema=False, response_class=HTMLResponse)
def app_download_page(request: Request):
    apk_path = get_latest_apk_path()
    apk_status = f"disponivel: {apk_path.name}" if apk_path else "nao encontrado"
    download_url = request.url_for("app_download")
    download_version = int(apk_path.stat().st_mtime) if apk_path else "missing"
    download_href = f"/app-download?v={download_version}"
    html = f"""
    <!doctype html>
    <html lang="pt-BR">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Baixar NFE Scanner</title>
        <style>
          body {{
            font-family: Arial, sans-serif;
            background: #f7f7f5;
            color: #29292e;
            margin: 0;
            padding: 24px;
          }}
          .card {{
            max-width: 520px;
            margin: 0 auto;
            background: #fff;
            border: 1px solid #dbd6cc;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, .08);
          }}
          h1 {{ margin-top: 0; font-size: 24px; }}
          .button {{
            display: block;
            margin-top: 18px;
            padding: 16px 18px;
            border-radius: 12px;
            background: #f29129;
            color: #111;
            text-align: center;
            text-decoration: none;
            font-weight: 700;
          }}
          code {{
            display: block;
            margin-top: 16px;
            padding: 12px;
            background: #fff2de;
            border-radius: 8px;
            word-break: break-all;
          }}
          small {{ color: #66666b; }}
        </style>
      </head>
      <body>
        <main class="card">
          <h1>NFE Scanner Android</h1>
          <p>APK {apk_status}. Toque no botao abaixo para baixar e instalar no Android.</p>
          <a class="button" href="{download_href}">Baixar APK</a>
          <code>{download_url}?v={download_version}</code>
          <small>Se o Android bloquear, permita instalar apps desconhecidos para o navegador usado.</small>
        </main>
      </body>
    </html>
    """
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


@app.get("/", include_in_schema=False, response_class=RedirectResponse)
def root():
    return RedirectResponse("/painel")


@app.post(
    "/auth/login/",
    response_model=schemas.AuthResponse,
    tags=["Sistema"],
    summary="Autenticar usuario do painel",
)
def auth_login(login_data: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario ou senha invalidos.")

    token = create_session_token(user.username)
    response.set_cookie("session", token, httponly=True, samesite="lax")
    logger.info("Login realizado | username=%s", user.username)
    return {"access_token": token}


@app.post(
    "/auth/logout/",
    tags=["Sistema"],
    summary="Encerrar sessao do painel",
)
def auth_logout(response: Response):
    response.delete_cookie("session")
    return {"detail": "Sessao encerrada."}


@app.get(
    "/auth/me/",
    response_model=schemas.UserResponse,
    tags=["Sistema"],
    summary="Informacoes do usuario autenticado",
)
def auth_me(current_user: models.User = Depends(get_current_user)):
    return current_user


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
def read_barcode(
    barcode_data: schemas.BarcodeInput,
    current_user: models.User = Depends(get_current_user),
):
    ensure_not_viewer(current_user)
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
def importar_barcode(
    barcode_data: schemas.BarcodeImportInput,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_not_viewer(current_user)
    barcode_result = read_barcode(barcode_data, current_user)
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
    "/notas/importar-remessa/",
    response_model=schemas.BarcodeBatchResponse,
    tags=["Notas fiscais"],
    summary="Consultar e cadastrar notas por remessa",
    description=(
        "Recebe uma ou mais chaves de NF-e, consulta a API fiscal e cadastra as notas "
        "em lote. Quando uma chave nao e reconhecida ou a API falha, registra a chave "
        "como nota com erro no painel para tratamento posterior."
    ),
)
def importar_remessa(
    remessa_data: schemas.BarcodeBatchInput,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_not_viewer(current_user)
    itens = []
    cadastradas = erros = duplicadas = invalidas = 0

    for raw_code in remessa_data.chaves:
        raw_code = (raw_code or "").strip()
        if not raw_code:
            continue

        try:
            chave_acesso = barcode_service.extract_access_key(raw_code)
        except ValueError as error:
            invalidas += 1
            chave_erro = raw_code[:100]
            detalhe = str(error)
            try:
                nota = crud.create_nota_erro(
                    db,
                    schemas.NotaFiscalErrorCreate(chave_acesso=chave_erro, local=remessa_data.local.value, detalhe=detalhe),
                )
                itens.append(
                    schemas.BarcodeBatchItem(
                        chave_acesso=chave_erro,
                        status="erro",
                        detalhe=f"Chave invalida registrada com erro: {detalhe}",
                        id=nota.id,
                    )
                )
                erros += 1
            except IntegrityError:
                duplicadas += 1
                itens.append(
                    schemas.BarcodeBatchItem(
                        chave_acesso=chave_erro,
                        status="duplicada",
                        detalhe="Chave invalida ja cadastrada anteriormente.",
                    )
                )
            continue

        try:
            nota_api = integra_api.consultar_nfe(chave_acesso)
            nota_data = schemas.NotaFiscalCreate(**nota_api, local=remessa_data.local)
            nota = crud.create_nota(db, nota_data)
            cadastradas += 1
            itens.append(
                schemas.BarcodeBatchItem(
                    chave_acesso=chave_acesso,
                    status="cadastrada",
                    detalhe="Nota cadastrada com sucesso.",
                    id=nota.id,
                    numero_nf=nota.numero_nf,
                )
            )
            logger.info("Nota importada por remessa | id=%s | numero=%s | local=%s", nota.id, nota.numero_nf, nota.local)
        except IntegrityError:
            duplicadas += 1
            itens.append(
                schemas.BarcodeBatchItem(
                    chave_acesso=chave_acesso,
                    status="duplicada",
                    detalhe="Nota fiscal ja cadastrada para esta chave de acesso.",
                )
            )
            logger.warning("Importacao por remessa duplicada | chave=%s", mask_access_key(chave_acesso))
        except Exception as error:
            detalhe = str(error)[:2000] or "Falha ao consultar ou salvar a nota."
            try:
                nota = crud.create_nota_erro(
                    db,
                    schemas.NotaFiscalErrorCreate(chave_acesso=chave_acesso, local=remessa_data.local.value, detalhe=detalhe),
                )
                erros += 1
                itens.append(
                    schemas.BarcodeBatchItem(
                        chave_acesso=chave_acesso,
                        status="erro",
                        detalhe=detalhe,
                        id=nota.id,
                    )
                )
                logger.error(
                    "Nota da remessa registrada com erro | id=%s | chave=%s | detalhe=%s",
                    nota.id,
                    mask_access_key(chave_acesso),
                    detalhe,
                )
            except IntegrityError:
                duplicadas += 1
                itens.append(
                    schemas.BarcodeBatchItem(
                        chave_acesso=chave_acesso,
                        status="duplicada",
                        detalhe="Nota fiscal ja cadastrada para esta chave de acesso.",
                    )
                )

    return schemas.BarcodeBatchResponse(
        total=len(itens),
        cadastradas=cadastradas,
        erros=erros,
        duplicadas=duplicadas,
        invalidas=invalidas,
        itens=itens,
    )


@app.post(
    "/notas/",
    response_model=schemas.NotaFiscalResponse,
    tags=["Notas fiscais"],
    summary="Cadastrar nota fiscal",
    description=(
        "Grava no banco uma nota fiscal ja conferida pelo usuario no aplicativo. "
        "O local e obrigatorio e aceita CDMA ou PRU. "
        "Nos lancamentos feitos pelo app, faturista deve ser BIPE. "
        "No fluxo principal, use este endpoint depois da leitura por /barcode-nf/ "
        "e da confirmacao manual dos dados.\n\n"
        "No botao 'Salvar e proxima', o app chama este endpoint para gravar a nota "
        "atual e depois volta ao leitor. No botao 'Salvar e finalizar', "
        "tambem chama este endpoint e encerra o fluxo."
    ),
)
def create_nota(
    nota_data: schemas.NotaFiscalCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_not_viewer(current_user)
    try:
        nota = crud.create_nota(db, nota_data, nota_data.caminho_arquivo_imagem)
    except IntegrityError as error:
        logger.warning("Cadastro duplicado | chave=%s", mask_access_key(nota_data.chave_acesso))
        raise HTTPException(status_code=409, detail="Nota fiscal ja cadastrada para esta chave de acesso.") from error
    logger.info("Nota cadastrada | id=%s | numero=%s | local=%s", nota.id, nota.numero_nf, nota.local)
    return nota


@app.post(
    "/notas/erro/",
    response_model=schemas.NotaFiscalResponse,
    tags=["Notas fiscais"],
    summary="Registrar nota que falhou ao salvar",
    description=(
        "Registra a chave de uma nota que nao pode ser salva normalmente. "
        "O painel identifica o registro e apresenta os demais campos como ERRO. "
        "Uma chave ja cadastrada continua retornando conflito."
    ),
    responses={409: {"description": "Nota fiscal ja cadastrada para esta chave de acesso."}},
)
def create_nota_erro(
    erro_data: schemas.NotaFiscalErrorCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_not_viewer(current_user)
    try:
        nota = crud.create_nota_erro(db, erro_data)
    except IntegrityError as error:
        logger.warning("Registro de erro duplicado | chave=%s", mask_access_key(erro_data.chave_acesso))
        raise HTTPException(status_code=409, detail="Nota fiscal ja cadastrada para esta chave de acesso.") from error
    logger.error(
        "Falha de salvamento registrada | id=%s | chave=%s | detalhe=%s",
        nota.id,
        mask_access_key(nota.chave_acesso),
        erro_data.detalhe,
    )
    return nota


@app.post(
    "/notas/erro/refresh/",
    response_model=schemas.NotaFiscalErrorRefreshResponse,
    tags=["Notas fiscais"],
    summary="Atualizar notas sinalizadas com erro",
    description=(
        "Consulta novamente na API fiscal somente as chaves dos registros cujo campo "
        "Produto contenha ERRO. Quando a consulta tem sucesso, atualiza a mesma linha "
        "e preserva o local selecionado originalmente."
    ),
)
def refresh_notas_erro(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin(current_user)
    notas_erro = crud.get_notas_erro(db)
    itens = []
    atualizadas = 0

    for nota in notas_erro:
        chave_acesso = nota.chave_acesso or ""
        try:
            chave_acesso = barcode_service.extract_access_key(chave_acesso)
            nota_data = integra_api.consultar_nfe(chave_acesso)
            crud.resolve_nota_erro(db, nota, nota_data)
            atualizadas += 1
            detalhe = "Atualizada com sucesso."
            atualizado = True
            logger.info("Nota com erro atualizada | id=%s | chave=%s", nota.id, mask_access_key(chave_acesso))
        except Exception as error:
            detalhe = str(error)
            atualizado = False
            db.rollback()
            crud.update_nota_erro_detalhe(db, nota, detalhe)
            logger.warning(
                "Nota com erro permaneceu pendente | id=%s | chave=%s | motivo=%s",
                nota.id,
                mask_access_key(chave_acesso),
                detalhe,
            )
        itens.append(
            schemas.NotaFiscalErrorRefreshItem(
                chave_acesso=chave_acesso,
                atualizado=atualizado,
                detalhe=detalhe,
            )
        )

    return schemas.NotaFiscalErrorRefreshResponse(
        encontradas=len(notas_erro),
        atualizadas=atualizadas,
        falhas=len(notas_erro) - atualizadas,
        itens=itens,
    )


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
    data_cadastro_inicio: datetime | None = Query(None, description="Inicio do periodo de bip."),
    data_cadastro_fim: datetime | None = Query(None, description="Fim do periodo de bip."),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_notas(
        db,
        skip=skip,
        limit=limit,
        data_cadastro_inicio=data_cadastro_inicio,
        data_cadastro_fim=data_cadastro_fim,
    )


@app.get(
    "/relatorios/operacional/",
    response_model=schemas.RelatorioOperacionalResponse,
    tags=["Notas fiscais"],
    summary="Resumo operacional diario e mensal",
    description=(
        "Agrupa por produto as quantidades das notas sem erro, considerando a data de "
        "emissao. Retorna os acumulados do mes vigente e do dia vigente em toneladas."
    ),
)
def relatorio_operacional(
    data_inicio: datetime | None = Query(None, description="Data e hora inicial inclusiva."),
    data_fim: datetime | None = Query(None, description="Data e hora final inclusiva."),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data_inicio and data_fim:
        if data_inicio > data_fim:
            raise HTTPException(status_code=400, detail="A data inicial deve ser anterior ou igual a data final.")
        if data_fim.second == 0 and data_fim.microsecond == 0:
            data_fim = data_fim.replace(second=59, microsecond=999999)
        inicio_mes = inicio_dia = data_inicio
        fim_mes = fim_dia = data_fim
    else:
        agora = datetime.now()
        inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fim_mes = agora.replace(
            day=monthrange(agora.year, agora.month)[1],
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )
        inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        fim_dia = agora.replace(hour=23, minute=59, second=59, microsecond=999999)
    return crud.get_relatorio_operacional(db, inicio_mes, fim_mes, inicio_dia, fim_dia)


@app.get(
    "/relatorios/material/",
    response_model=schemas.RelatorioMaterialResponse,
    tags=["Notas fiscais"],
    summary="Resumo de materiais por periodo",
    description=(
        "Agrupa notas sem erro por material dentro do periodo informado, usando a "
        "data de emissao. Retorna quantidade em toneladas e quantidade de NF-es."
    ),
)
def relatorio_material(
    data_inicio: datetime = Query(description="Data e hora inicial inclusiva."),
    data_fim: datetime = Query(description="Data e hora final inclusiva."),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data_inicio > data_fim:
        raise HTTPException(status_code=400, detail="A data inicial deve ser anterior ou igual a data final.")
    if data_fim.second == 0 and data_fim.microsecond == 0:
        data_fim = data_fim.replace(second=59, microsecond=999999)
    return crud.get_relatorio_material(db, data_inicio, data_fim)


@app.get(
    "/relatorios/material-local/",
    response_model=schemas.RelatorioMaterialLocalResponse,
    tags=["Notas fiscais"],
    summary="Resumo de materiais por periodo e local",
    description=(
        "Agrupa notas sem erro por material e separa quantidade em toneladas e "
        "quantidade de NF-es entre os locais CDMA e PRU."
    ),
)
def relatorio_material_local(
    data_inicio: datetime = Query(description="Data e hora inicial inclusiva."),
    data_fim: datetime = Query(description="Data e hora final inclusiva."),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data_inicio > data_fim:
        raise HTTPException(status_code=400, detail="A data inicial deve ser anterior ou igual a data final.")
    if data_fim.second == 0 and data_fim.microsecond == 0:
        data_fim = data_fim.replace(second=59, microsecond=999999)
    return crud.get_relatorio_material_local(db, data_inicio, data_fim)


@app.get(
    "/relatorios/recebimento-diario/",
    response_model=schemas.RelatorioRecebimentoResponse,
    tags=["Notas fiscais"],
    summary="Composicao diaria por material",
    description=(
        "Agrupa as quantidades recebidas por dia e separa proporcionalmente cada "
        "material em uma barra empilhada. O filtro de material e opcional."
    ),
)
def relatorio_recebimento_diario(
    data_inicio: datetime = Query(description="Data e hora inicial inclusiva."),
    data_fim: datetime = Query(description="Data e hora final inclusiva."),
    material: str | None = Query(None, description="Material especifico. Omitir para considerar todos."),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data_inicio > data_fim:
        raise HTTPException(status_code=400, detail="A data inicial deve ser anterior ou igual a data final.")
    if data_fim.second == 0 and data_fim.microsecond == 0:
        data_fim = data_fim.replace(second=59, microsecond=999999)
    return crud.get_relatorio_recebimento(db, data_inicio, data_fim, material)


@app.get(
    "/relatorios/exportar/",
    response_class=StreamingResponse,
    tags=["Notas fiscais"],
    summary="Exportar relatorio operacional",
    description="Gera o relatorio completo em PDF ou Excel usando os periodos configurados no painel.",
)
def exportar_relatorio_operacional(
    formato: str = Query(pattern="^(pdf|xlsx)$"),
    data_inicio: datetime | None = Query(None),
    data_fim: datetime | None = Query(None),
    material_inicio: datetime | None = Query(None),
    material_fim: datetime | None = Query(None),
    setor_inicio: datetime | None = Query(None),
    setor_fim: datetime | None = Query(None),
    recebimento_inicio: datetime | None = Query(None),
    recebimento_fim: datetime | None = Query(None),
    recebimento_material: str | None = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data_inicio and data_fim:
        material_inicio = setor_inicio = recebimento_inicio = data_inicio
        material_fim = setor_fim = recebimento_fim = data_fim
    if not all([material_inicio, material_fim, setor_inicio, setor_fim, recebimento_inicio, recebimento_fim]):
        raise HTTPException(status_code=400, detail="Informe o periodo inicial e final do relatorio.")
    if material_inicio > material_fim or setor_inicio > setor_fim or recebimento_inicio > recebimento_fim:
        raise HTTPException(status_code=400, detail="A data inicial deve ser anterior ou igual a data final.")
    if material_fim.second == 0 and material_fim.microsecond == 0:
        material_fim = material_fim.replace(second=59, microsecond=999999)
    if setor_fim.second == 0 and setor_fim.microsecond == 0:
        setor_fim = setor_fim.replace(second=59, microsecond=999999)
    if recebimento_fim.second == 0 and recebimento_fim.microsecond == 0:
        recebimento_fim = recebimento_fim.replace(second=59, microsecond=999999)

    agora = datetime.now()
    inicio_mes = inicio_dia = material_inicio
    fim_mes = fim_dia = material_fim
    operacional = crud.get_relatorio_operacional(db, inicio_mes, fim_mes, inicio_dia, fim_dia)
    material = crud.get_relatorio_material(db, material_inicio, material_fim)
    setor = crud.get_relatorio_material_local(db, setor_inicio, setor_fim)
    recebimento = crud.get_relatorio_recebimento(db, recebimento_inicio, recebimento_fim, recebimento_material)

    timestamp = agora.strftime("%Y%m%d_%H%M%S")
    filename = f"relatorio_operacional_{timestamp}.{formato}"
    output = BytesIO()
    if formato == "pdf":
        report_service.generate_operational_pdf(operacional, material, setor, recebimento, output)
        media_type = "application/pdf"
    else:
        report_service.generate_operational_excel(operacional, material, setor, recebimento, output)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    output.seek(0)
    return StreamingResponse(
        output,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
def update_nota(nota_id: int, nota_data: schemas.NotaFiscalUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_admin(current_user)
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
def delete_nota(nota_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_admin(current_user)
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
def create_faturista(faturista_data: schemas.FaturistaCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_admin(current_user)
    try:
        faturista = crud.create_faturista(db, faturista_data)
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="Faturista ja cadastrado.") from error
    logger.info("Faturista cadastrado | id=%s | nome=%s | admin=%s", faturista.id, faturista.nome, current_user.username)
    return faturista


@app.get(
    "/faturistas/",
    response_model=list[schemas.FaturistaResponse],
    tags=["Faturistas"],
    summary="Listar faturistas",
)
def list_faturistas(
    incluir_inativos: bool = Query(False, description="Inclui faturistas desativados."),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin(current_user)
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin(current_user)
    atual = crud.get_faturista(db, faturista_id)
    if not atual:
        raise HTTPException(status_code=404, detail="Faturista nao encontrado.")
    if atual.nome == "BIPE" and (faturista_data.nome != "BIPE" or not faturista_data.ativo):
        raise HTTPException(status_code=409, detail="O faturista padrao BIPE nao pode ser renomeado ou desativado.")
    if atual.nome == VIEWER_USERNAME and faturista_data.nome != VIEWER_USERNAME:
        raise HTTPException(status_code=409, detail="O usuario de visualizacao nao pode ser renomeado.")
    try:
        faturista = crud.update_faturista(db, faturista_id, faturista_data)
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="Ja existe um faturista com este nome.") from error
    logger.info("Faturista atualizado | id=%s | nome=%s | ativo=%s | admin=%s", faturista.id, faturista.nome, faturista.ativo, current_user.username)
    return faturista


@app.delete(
    "/faturistas/{faturista_id}/",
    response_model=schemas.FaturistaDeleteResponse,
    tags=["Faturistas"],
    summary="Excluir faturista",
    responses={404: {"description": "Faturista nao encontrado."}, 409: {"description": "BIPE nao pode ser excluido."}},
)
def delete_faturista(faturista_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_admin(current_user)
    atual = crud.get_faturista(db, faturista_id)
    if not atual:
        raise HTTPException(status_code=404, detail="Faturista nao encontrado.")
    if atual.nome == "BIPE":
        raise HTTPException(status_code=409, detail="O faturista padrao BIPE nao pode ser excluido.")
    if atual.nome == VIEWER_USERNAME:
        raise HTTPException(status_code=409, detail="O usuario de visualizacao nao pode ser excluido.")
    faturista = crud.delete_faturista(db, faturista_id)
    logger.info("Faturista excluido | id=%s | nome=%s | admin=%s", faturista.id, faturista.nome, current_user.username)
    return schemas.FaturistaDeleteResponse(
        id=faturista.id,
        nome=faturista.nome,
        mensagem="Faturista excluido com sucesso.",
    )


@app.post(
    "/relatorio/",
    response_class=StreamingResponse,
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
    current_user: models.User = Depends(get_current_user),
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
    ensure_not_viewer(current_user)
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

    if nota_id:
        filtros_str = f"Nota ID: {nota_id}"
    else:
        filtros_str = (
            f"Periodo: {data_inicio or 'inicio'} a {data_fim or 'fim'} | "
            f"Fornecedor: {fornecedor or 'todos'} | "
            f"Valor minimo: {valor_min if valor_min is not None else 'todos'} | "
            f"Valor maximo: {valor_max if valor_max is not None else 'todos'}"
        )

    output = BytesIO()
    report_service.generate_xml(notas, filtros_str, output)
    output.seek(0)
    logger.info("XML gerado | nota_id=%s | quantidade=%s | arquivo=%s", nota_id, len(notas), filename)

    return StreamingResponse(
        output,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
