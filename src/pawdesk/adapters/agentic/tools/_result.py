"""Contrato estruturado de retorno de ferramentas para o LLM."""

from pawdesk.application.constants import ErrorCode


class ToolResult:
    """Padroniza retornos das tools como dicts estruturados sem exceções vazadas."""

    @staticmethod
    def ok(**data: object) -> dict[str, object]:
        return {"status": "success", **data}

    @staticmethod
    def fail(code: ErrorCode, message: str, **extra: object) -> dict[str, object]:
        return {"status": "error", "error_code": code.value, "message": message, **extra}
