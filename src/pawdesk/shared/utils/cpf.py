"""Validação e mascaramento de CPF (nunca armazenar/logar o número completo)."""

from pawdesk.shared.constants.regex import NON_DIGITS_RE


def last_digits(value: str, count: int = 3) -> str:
    """Extrai os últimos dígitos numéricos de um CPF ou string."""
    digits = NON_DIGITS_RE.sub("", value)
    if len(digits) < count:
        raise ValueError(f"Esperados pelo menos {count} dígitos.")
    return digits[-count:]


def is_valid_cpf(cpf: str) -> bool:
    """Valida os dígitos verificadores de um CPF brasileiro."""
    digits = NON_DIGITS_RE.sub("", cpf)
    if len(digits) != 11 or len(set(digits)) == 1:
        return False

    for check_pos in (9, 10):
        total = sum(int(digits[idx]) * ((check_pos + 1) - idx) for idx in range(check_pos))
        expected = (total * 10) % 11
        if expected == 10:
            expected = 0
        if int(digits[check_pos]) != expected:
            return False
    return True


def mask_cpf(cpf: str) -> str:
    """Mascara um CPF mantendo apenas indício mínimo não sensível."""
    digits = NON_DIGITS_RE.sub("", cpf)
    if len(digits) != 11:
        return "***"
    return f"***.***.*{digits[-3:-2]}-{digits[-2:]}"
