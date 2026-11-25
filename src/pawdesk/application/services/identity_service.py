"""Coordenação de resolução e elevação de identidade em dois níveis (RN-01)."""

from pawdesk.application.dto.context import CallerContext
from pawdesk.application.ports.outbound.infra import Clock
from pawdesk.application.ports.outbound.repositories import (
    ConversationRepository,
    CustomerRepository,
    OrderRepository,
)
from pawdesk.domain.constants import VerificationLevel
from pawdesk.domain.entities.conversation import Conversation
from pawdesk.domain.services.identity_verification_policy import (
    IdentityVerificationPolicy,
    VerificationDecision,
)
from pawdesk.domain.value_objects.ids import ConversationId, OrderNumber
from pawdesk.domain.value_objects.phone import PhoneE164


class IdentityService:
    """Resolve Nível 1 pelo telefone da conversa e coordena Nível 2 (step-up)."""

    def __init__(
        self,
        customers: CustomerRepository,
        orders: OrderRepository,
        conversations: ConversationRepository,
        policy: IdentityVerificationPolicy,
        clock: Clock,
    ) -> None:
        self._customers = customers
        self._orders = orders
        self._conversations = conversations
        self._policy = policy
        self._clock = clock

    async def resolve_caller(self, conv: Conversation, correlation_id: str) -> CallerContext:
        customer = None
        if conv.customer_id is not None:
            customer = await self._customers.get_by_id(conv.customer_id)
        else:
            try:
                phone = PhoneE164(conv.channel_user_phone)
                customer = await self._customers.get_by_phone(phone)
            except Exception:
                customer = None

        level = conv.verification_level
        if customer is not None and level < VerificationLevel.PHONE_MATCH:
            level = VerificationLevel.PHONE_MATCH
            await self._conversations.update_identity(
                conv.id,
                customer_id=customer.id,
                level=level,
                attempts=conv.verification_attempts,
                blocked_until=conv.blocked_until,
            )

        return CallerContext(
            customer_id=customer.id if customer is not None else conv.customer_id,
            customer_first_name=customer.first_name if customer is not None else None,
            level=level,
            conversation_id=conv.id.value,
            correlation_id=correlation_id,
        )

    async def evaluate_step_up(
        self,
        *,
        caller: CallerContext,
        order_number: OrderNumber,
        cpf_last3: str,
    ) -> VerificationDecision:
        conv = await self._conversations.get_by_id(ConversationId(caller.conversation_id))
        if conv is None or caller.customer_id is None:
            return VerificationDecision(
                verified=False,
                new_level=VerificationLevel.NONE,
                attempts=0,
                blocked_until=None,
                should_handoff=False,
                reason="CUSTOMER_NOT_IDENTIFIED",
            )

        customer = await self._customers.get_by_id(caller.customer_id)
        if customer is None:
            return VerificationDecision(
                verified=False,
                new_level=VerificationLevel.NONE,
                attempts=conv.verification_attempts,
                blocked_until=conv.blocked_until,
                should_handoff=False,
                reason="CUSTOMER_NOT_FOUND",
            )

        order = await self._orders.get_by_number(order_number)
        decision = self._policy.evaluate_step_up(
            customer=customer,
            order=order,
            cpf_last3_input=cpf_last3,
            current_attempts=conv.verification_attempts,
            blocked_until=conv.blocked_until,
            now=self._clock.now(),
        )
        await self._conversations.update_identity(
            conv.id,
            customer_id=customer.id,
            level=decision.new_level,
            attempts=decision.attempts,
            blocked_until=decision.blocked_until,
        )
        return decision
