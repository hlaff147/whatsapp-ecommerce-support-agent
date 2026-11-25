"""Value Object de telefone E.164."""

from dataclasses import dataclass

from pawdesk.domain.errors import InvalidPhoneNumber
from pawdesk.shared.utils.phone import to_e164


@dataclass(frozen=True)
class PhoneE164:
    value: str

    def __post_init__(self) -> None:
        try:
            normalized = to_e164(self.value)
        except ValueError as exc:
            raise InvalidPhoneNumber("Número de telefone inválido.") from exc
        object.__setattr__(self, "value", normalized)
