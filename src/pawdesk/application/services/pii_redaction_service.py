"""Serviço de mascaramento de PII para logs, auditoria e transcrições."""

from pawdesk.shared.utils.masking import redact_pii

_SENSITIVE_ARG_KEYS = frozenset({"cpf", "cpf_last3", "phone", "email", "token", "secret"})


class PiiRedactionService:
    """Centraliza a redação de dados pessoais antes de persistir ou logar."""

    def redact_text(self, text: str) -> str:
        return redact_pii(text)

    def redact_args(self, args: dict[str, object]) -> dict[str, object]:
        redacted: dict[str, object] = {}
        for key, value in args.items():
            if key.lower() in _SENSITIVE_ARG_KEYS:
                redacted[key] = "[REDACTED]"
            elif isinstance(value, str):
                redacted[key] = redact_pii(value)
            else:
                redacted[key] = value
        return redacted
