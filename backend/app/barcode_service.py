import re


def extract_access_key(raw_code: str) -> str:
    digits = re.sub(r"\D", "", raw_code or "")

    if len(digits) != 44:
        raise ValueError("A chave de acesso da NF-e deve conter exatamente 44 digitos.")

    return digits
