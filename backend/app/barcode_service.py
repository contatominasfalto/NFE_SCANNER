import re


def extract_access_key(raw_code: str) -> str:
    digits = re.sub(r"\D", "", raw_code or "")

    if len(digits) != 44:
        raise ValueError("A chave de acesso da NF-e deve conter exatamente 44 digitos.")

    expected_digit = calculate_check_digit(digits[:-1])
    if digits[-1] != expected_digit:
        raise ValueError(
            "Chave de acesso com digito verificador invalido. "
            f"DV informado: {digits[-1]}, DV esperado: {expected_digit}."
        )

    return digits


def calculate_check_digit(access_key_without_digit: str) -> str:
    total = 0
    weight = 2
    for digit in reversed(access_key_without_digit):
        total += int(digit) * weight
        weight += 1
        if weight > 9:
            weight = 2

    remainder = total % 11
    check_digit = 11 - remainder
    return "0" if check_digit >= 10 else str(check_digit)
