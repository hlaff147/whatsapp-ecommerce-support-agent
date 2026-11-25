"""Value Object de código de rastreio."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackingCode:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if len(normalized) < 6:
            raise ValueError("Código de rastreio inválido.")
        object.__setattr__(self, "value", normalized)
