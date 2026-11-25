"""Normalização e validação de telefones no padrão E.164."""

from pawdesk.shared.constants.regex import NON_DIGITS_RE


def to_e164(raw_phone: str, default_country_code: str = "55") -> str:
    """Converte um telefone informado para o formato E.164 (ex.: +5511999990001)."""
    digits = NON_DIGITS_RE.sub("", raw_phone)
    if not digits:
        raise ValueError("Telefone vazio.")
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) in {10, 11} and not digits.startswith(default_country_code):
        digits = f"{default_country_code}{digits}"
    if len(digits) < 10 or len(digits) > 15:
        raise ValueError("Quantidade de dígitos inválida para telefone E.164.")
    return f"+{digits}"


def is_valid_br_mobile(raw_phone: str) -> bool:
    """Verifica se o número é um celular brasileiro válido no padrão +55DD9XXXXXXXX."""
    try:
        e164 = to_e164(raw_phone)
    except ValueError:
        return False
    digits = e164[1:]
    return len(digits) == 13 and digits.startswith("55") and digits[4] == "9"
