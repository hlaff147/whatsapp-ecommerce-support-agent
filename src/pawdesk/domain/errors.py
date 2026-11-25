"""Exceções de domínio (violações puras de regra de negócio)."""


class DomainError(Exception):
    """Violação de regra de negócio. `user_message` pode ser exibida ao cliente."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class InvalidOrderNumber(DomainError):
    """Número de pedido inválido."""


class InvalidZipCode(DomainError):
    """CEP inválido."""


class InvalidPhoneNumber(DomainError):
    """Número de telefone inválido."""


class ReturnNotAllowed(DomainError):
    """Solicitação de troca/devolução violou elegibilidade."""
