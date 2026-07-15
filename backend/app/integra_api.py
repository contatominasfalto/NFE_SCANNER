import json
import logging
import re
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .config import MEUDANFE_API_BASE_URL, MEUDANFE_API_KEY
from .logging_config import mask_access_key


class IntegracaoAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


logger = logging.getLogger("nfe_scanner.integracao")


def consultar_nfe(chave_acesso: str) -> dict:
    masked_key = mask_access_key(chave_acesso)
    if not MEUDANFE_API_KEY:
        logger.error("Consulta fiscal bloqueada: MEUDANFE_API_KEY nao configurada")
        raise IntegracaoAPIError("Integracao fiscal nao configurada no servidor.", status_code=503)

    url = f"{MEUDANFE_API_BASE_URL.rstrip('/')}/{quote(chave_acesso)}"
    logger.info("Consultando API fiscal | chave=%s", masked_key)
    request = Request(
        url,
        headers={
            "api-key": MEUDANFE_API_KEY,
            "Accept": "application/json, application/xml, text/xml",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read()
            logger.info(
                "API fiscal respondeu | chave=%s | status=%s | bytes=%s",
                masked_key,
                response.status,
                len(payload),
            )
    except HTTPError as error:
        if error.code == 404:
            logger.warning("Nota nao encontrada na API fiscal | chave=%s | status=404", masked_key)
            raise IntegracaoAPIError(
                "Nota fiscal nao encontrada na API fiscal. Confirme a chave ou tente novamente mais tarde.",
                status_code=404,
            ) from error
        logger.error("Falha HTTP na API fiscal | chave=%s | status=%s", masked_key, error.code)
        raise IntegracaoAPIError(f"API fiscal indisponivel ou recusou a consulta (HTTP {error.code}).") from error
    except URLError as error:
        logger.error("Falha de conexao com API fiscal | chave=%s | motivo=%s", masked_key, error.reason)
        raise IntegracaoAPIError("Nao foi possivel acessar a API fiscal.", status_code=503) from error

    try:
        xml_content = extract_xml_content(payload)
        nota = parse_nfe_xml(xml_content, chave_acesso)
    except IntegracaoAPIError:
        logger.exception("Resposta fiscal invalida | chave=%s", masked_key)
        raise

    logger.info(
        "Nota fiscal consultada | chave=%s | numero=%s | fornecedor=%s",
        masked_key,
        nota["numero_nf"],
        nota["nome_fornecedor"],
    )
    return nota


def extract_xml_content(payload: bytes) -> bytes:
    stripped = payload.lstrip()
    if stripped.startswith(b"<"):
        return payload

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IntegracaoAPIError("Resposta da API fiscal nao contem XML valido.") from error

    if isinstance(data, str):
        return data.encode("utf-8")

    if isinstance(data, dict):
        for key in ("xml", "data", "response", "content"):
            value = data.get(key)
            if isinstance(value, str) and value.lstrip().startswith("<"):
                return value.encode("utf-8")

    raise IntegracaoAPIError("Resposta da API fiscal nao contem XML da NF-e.")


def parse_nfe_xml(xml_content: bytes, chave_acesso: str) -> dict:
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as error:
        if "unbound prefix" not in str(error):
            raise IntegracaoAPIError("XML retornado pela API fiscal e invalido.") from error
        sanitized_content = sanitize_unbound_prefix_xml(xml_content)
        try:
            root = ElementTree.fromstring(sanitized_content)
            logger.warning(
                "XML da API fiscal sanitizado por prefixo invalido | chave=%s",
                mask_access_key(chave_acesso),
            )
        except ElementTree.ParseError as sanitized_error:
            raise IntegracaoAPIError("XML retornado pela API fiscal e invalido.") from sanitized_error

    data_emissao = find_text(root, "dhEmi") or find_text(root, "dEmi")
    produtos = find_all_text(root, "xProd")

    return {
        "numero_nf": find_text(root, "nNF"),
        "serie": find_text(root, "serie"),
        "data_emissao": parse_datetime(data_emissao),
        "cnpj_fornecedor": find_text(root, "CNPJ"),
        "nome_fornecedor": find_text(root, "xNome"),
        "valor_total": parse_float(find_text(root, "vNF")),
        "chave_acesso": chave_acesso,
        "produto": "; ".join(dict.fromkeys(produtos)) or None,
        "quantidade": parse_optional_float(find_text(root, "pesoL")),
        "transportador": find_nested_text(root, "transporta", "xNome") or None,
        "faturista": "BIPE",
        "observacao": find_text(root, "infCpl") or None,
    }


def sanitize_unbound_prefix_xml(xml_content: bytes) -> bytes:
    text = xml_content.decode("utf-8", errors="replace")
    text = re.sub(r"<xmlns:[^>]+>.*?</xmlns:[^>]+>", "", text)
    text = re.sub(r"\sxmlns:[A-Za-z_][\w.-]*=\"[^\"]*\"", "", text)
    text = re.sub(r"(<\/?)[A-Za-z_][\w.-]*:", r"\1", text)
    text = re.sub(r"\s[A-Za-z_][\w.-]*:([A-Za-z_][\w.-]*)=", r" \1=", text)
    return text.encode("utf-8")


def find_text(root, tag_name: str) -> str:
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == tag_name and element.text:
            return element.text.strip()
    return ""

def find_all_text(root, tag_name: str) -> list[str]:
    return [
        element.text.strip()
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == tag_name and element.text
    ]


def find_nested_text(root, parent_tag: str, child_tag: str) -> str:
    for parent in root.iter():
        if parent.tag.rsplit("}", 1)[-1] != parent_tag:
            continue
        return find_text(parent, child_tag)
    return ""


def parse_datetime(value: str) -> datetime:
    if not value:
        raise IntegracaoAPIError("XML da NF-e sem data de emissao.")

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError as error:
            raise IntegracaoAPIError("Data de emissao invalida no XML da NF-e.") from error


def parse_float(value: str) -> float:
    try:
        return float(value.replace(",", "."))
    except ValueError as error:
        raise IntegracaoAPIError("Valor total invalido no XML da NF-e.") from error


def parse_optional_float(value: str) -> float | None:
    if not value:
        return None
    return parse_float(value)
