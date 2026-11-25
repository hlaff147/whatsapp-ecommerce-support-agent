"""Política de verificação de identidade em dois níveis (RN-01)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from pawdesk.domain.constants import VerificationLevel
from pawdesk.domain.entities.customer import Customer
from pawdesk.domain.entities.order import Order
from pawdesk.shared.constants.limits import MAX_VERIFICATION_ATTEMPTS, VERIFICATION_LOCK_MINUTES
from pawdesk.shared.constants.regex import NON_DIGITS_RE
from pawdesk.shared.utils.hashing import constant_time_equals


@dataclass(frozen=True)
class VerificationDecision:
    verified: bool
    new_level: VerificationLevel
    attempts: int
    blocked_until: datetime | None
    should_handoff: bool
    reason: str | None = None


class IdentityVerificationPolicy:
    """Valida verificação reforçada (nº do pedido + 3 últimos dígitos do CPF)."""

    def __init__(
        self,
        max_attempts: int = MAX_VERIFICATION_ATTEMPTS,
        lock_minutes: int = VERIFICATION_LOCK_MINUTES,
    ) -> None:
        self._max_attempts = max_attempts
        self._lock_minutes = lock_minutes

    def evaluate_step_up(
        self,
        *,
        customer: Customer,
        order: Order | None,
        cpf_last3_input: str,
        current_attempts: int,
        blocked_until: datetime | None,
        now: datetime,
    ) -> VerificationDecision:
        """Avalia tentativa de elevação de identidade para STEP_UP (Nível 2)."""
        if blocked_until is not None and now < blocked_until:
            return VerificationDecision(
                verified=False,
                new_level=VerificationLevel.PHONE_MATCH,
                attempts=current_attempts,
                blocked_until=blocked_until,
                should_handoff=True,
                reason="BLOCKED",
            )

        digits = NON_DIGITS_RE.sub("", cpf_last3_input)
        order_belongs = order is not None and order.customer_id == customer.id
        cpf_matches = len(digits) == 3 and constant_time_equals(digits, customer.cpf_last3)

        if order_belongs and cpf_matches:
            return VerificationDecision(
                verified=True,
                new_level=VerificationLevel.STEP_UP,
                attempts=0,
                blocked_until=None,
                should_handoff=False,
            )

        next_attempts = current_attempts + 1
        if next_attempts >= self._max_attempts:
            return VerificationDecision(
                verified=False,
                new_level=VerificationLevel.PHONE_MATCH,
                attempts=next_attempts,
                blocked_until=now + timedelta(minutes=self._lock_minutes),
                should_handoff=True,
                reason="MAX_ATTEMPTS_EXCEEDED",
            )

        return VerificationDecision(
            verified=False,
            new_level=VerificationLevel.PHONE_MATCH,
            attempts=next_attempts,
            blocked_until=None,
            should_handoff=False,
            reason="MISMATCH",
        )
