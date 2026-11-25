"""Value Object monetário."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        quantized = Decimal(self.amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", quantized)

    def format_brl(self) -> str:
        """Formata no padrão brasileiro (ex.: R$ 189,90)."""
        formatted = f"{self.amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"

    def __gt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError("Moedas incompatíveis para comparação.")
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError("Moedas incompatíveis para comparação.")
        return self.amount >= other.amount
