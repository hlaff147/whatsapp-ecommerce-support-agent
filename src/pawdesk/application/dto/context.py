"""Contexto de identidade do chamador (fonte de verdade da aplicação)."""

from dataclasses import dataclass

from pawdesk.application.errors import VerificationRequired
from pawdesk.domain.constants import VerificationLevel
from pawdesk.domain.value_objects.ids import CustomerId


@dataclass(frozen=True)
class CallerContext:
    customer_id: CustomerId | None
    customer_first_name: str | None
    level: VerificationLevel
    conversation_id: str
    correlation_id: str

    def require(self, minimum: VerificationLevel) -> None:
        if minimum == VerificationLevel.NONE:
            return
        if self.customer_id is None or self.level < minimum:
            raise VerificationRequired(minimum)
