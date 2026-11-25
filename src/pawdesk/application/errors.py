"""Exceções da camada de aplicação."""

from pawdesk.domain.constants import VerificationLevel


class ApplicationError(Exception):
    """Erro base da camada de aplicação."""


class NotFound(ApplicationError):
    """Recurso solicitado não encontrado ou inacessível ao chamador."""

    def __init__(self, what: str) -> None:
        super().__init__(f"{what} não encontrado.")
        self.what = what


class VerificationRequired(ApplicationError):
    """Nível de verificação insuficiente para a operação."""

    def __init__(self, required_level: VerificationLevel) -> None:
        super().__init__(f"Verificação necessária: {required_level.name}")
        self.required_level = required_level


class VerificationBlocked(ApplicationError):
    """Cliente temporariamente bloqueado após exceder tentativas de verificação."""

    def __init__(self, message: str = "Verificação temporariamente bloqueada.") -> None:
        super().__init__(message)


class TransientError(ApplicationError):
    """Falha temporária elegível para retentativa na fila."""


class ExternalServiceUnavailable(TransientError):
    """Serviço externo indisponível no momento."""


class ConversationBusy(TransientError):
    """Lock distribuído da conversa já está em uso por outro worker."""


class AgentRuntimeError(ApplicationError):
    """Falha na execução do runtime agêntico."""
