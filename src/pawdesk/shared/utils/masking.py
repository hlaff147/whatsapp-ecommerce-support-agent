"""Mascaramento de PII para logs, auditoria e transcrições."""

from pawdesk.shared.constants.regex import CPF_RE, EMAIL_RE, NON_DIGITS_RE, PHONE_RE
from pawdesk.shared.utils.cpf import mask_cpf


def mask_email(email: str) -> str:
    """Mascara um endereço de e-mail preservando domínio."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    prefix = local[:2] if len(local) > 2 else local[:1]
    return f"{prefix}***@{domain}"


def mask_phone(phone: str) -> str:
    """Mascara um telefone mantendo apenas os 4 dígitos finais."""
    digits = NON_DIGITS_RE.sub("", phone)
    if len(digits) < 4:
        return "***"
    return f"***{digits[-4:]}"


def redact_pii(text: str) -> str:
    """Substitui CPF, e-mail e telefone em texto livre por marcadores seguros."""
    redacted = CPF_RE.sub(
        lambda m: mask_cpf(m.group(0)) if len(m.group(0)) >= 11 else "[CPF]", text
    )
    redacted = CPF_RE.sub("[CPF]", redacted)
    redacted = EMAIL_RE.sub("[EMAIL]", redacted)
    return PHONE_RE.sub("[TELEFONE]", redacted)
