"""Identificadores tipados do domínio."""

from dataclasses import dataclass

from pawdesk.domain.errors import InvalidOrderNumber
from pawdesk.shared.constants.regex import NON_DIGITS_RE, ORDER_NUMBER_RE


@dataclass(frozen=True)
class CustomerId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("CustomerId não pode ser vazio.")


@dataclass(frozen=True)
class ConversationId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ConversationId não pode ser vazio.")


@dataclass(frozen=True)
class Sku:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not normalized:
            raise ValueError("SKU não pode ser vazio.")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class OrderNumber:
    value: str

    def __post_init__(self) -> None:
        if not self.value.startswith("PD-") or len(self.value) < 8:
            raise InvalidOrderNumber(
                "Número do pedido inválido. O formato esperado é algo como PD-104822."
            )

    @classmethod
    def parse(cls, raw: str) -> "OrderNumber":
        """Normaliza formatos como 'pd 104822', '104822' ou 'PD-104822'."""
        cleaned = raw.strip().upper()
        match = ORDER_NUMBER_RE.search(cleaned)
        if match:
            return cls(f"PD-{match.group(1)}")
        digits = NON_DIGITS_RE.sub("", cleaned)
        if 5 <= len(digits) <= 8:
            return cls(f"PD-{digits}")
        raise InvalidOrderNumber(
            "Não reconheci esse número de pedido. Ele costuma começar com PD- seguido de números."
        )
