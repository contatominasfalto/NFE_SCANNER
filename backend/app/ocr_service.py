from datetime import datetime
import re

from PIL import Image
import pytesseract

from .config import TESSERACT_CMD

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def parse_brazilian_money(value: str) -> float:
    normalized = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return 0.0


def extract_nfe_data(image_path):
    """Extrai dados da NF usando OCR."""
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang="por")

    patterns = {
        "numero_nf": r"(?:N[ºo]\s*NF|NF-e|Nota\s*Fiscal|Numero|Número)[:\s]*(\d{3,12})",
        "serie": r"S[eé]rie[:\s]*(\d{1,3})",
        "data_emissao": r"(\d{2}/\d{2}/\d{4})",
        "cnpj_fornecedor": r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
        "nome_fornecedor": r"(?:RAZ[AÃ]O\s+SOCIAL|Fornecedor)[:\s]*([A-ZÀ-Ú0-9\s\.\-&]+)",
        "valor_total": r"(?:VALOR\s+TOTAL|TOTAL\s+DA\s+NOTA)[:\s]*R?\$?\s*([\d\.]+,\d{2})",
        "chave_acesso": r"(\d{44})",
    }

    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        result[key] = match.group(1).strip() if match else ""

    if not result["numero_nf"]:
        fallback = re.search(r"\b(\d{6,9})\b", text)
        result["numero_nf"] = fallback.group(1) if fallback else ""

    if result["data_emissao"]:
        try:
            result["data_emissao"] = datetime.strptime(result["data_emissao"], "%d/%m/%Y")
        except ValueError:
            result["data_emissao"] = datetime.now()
    else:
        result["data_emissao"] = datetime.now()

    result["valor_total"] = (
        parse_brazilian_money(result["valor_total"])
        if result["valor_total"]
        else 0.0
    )
    result["observacao"] = f"OCR extraido em {datetime.now():%d/%m/%Y %H:%M}"

    return result
