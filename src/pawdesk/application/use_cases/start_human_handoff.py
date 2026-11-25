"""Caso de uso: iniciar handoff humano explícito/administrativo."""

from collections.abc import Callable

from pawdesk.application.dto.context import CallerContext
from pawdesk.application.dto.results import OutboundMessage
from pawdesk.application.errors import NotFound
from pawdesk.application.messages import Messages
from pawdesk.application.ports.outbound.infra import Clock, TurnScheduler, UnitOfWork
from pawdesk.application.services.handoff_service import HandoffService
from pawdesk.domain.constants import HandoffPriority, HandoffReason
from pawdesk.domain.services.handoff_policy import HandoffDecision
from pawdesk.domain.value_objects.ids import ConversationId
from pawdesk.shared.utils.dates import is_business_hours
from pawdesk.shared.utils.ids import new_ulid


class StartHumanHandoff:
    """Transfere manualmente uma conversa para atendimento humano."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], UnitOfWork],
        handoff: HandoffService,
        scheduler: TurnScheduler,
        clock: Clock,
        messages: Messages,
    ) -> None:
        self._uow_factory = uow_factory
        self._handoff = handoff
        self._scheduler = scheduler
        self._clock = clock
        self._messages = messages

    async def execute(
        self,
        *,
        conversation_id: ConversationId,
        reason: HandoffReason,
        correlation_id: str,
    ) -> str:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            conv = await uow.conversations.get_by_id(conversation_id)
            if conv is None:
                raise NotFound("conversa")
            caller = CallerContext(
                customer_id=conv.customer_id,
                customer_first_name=None,
                level=conv.verification_level,
                conversation_id=conv.id.value,
                correlation_id=correlation_id,
            )
            decision = HandoffDecision(
                handoff=True,
                reason=reason,
                priority=HandoffPriority.HIGH,
                urgent=reason in {HandoffReason.LEGAL_RISK, HandoffReason.PET_HEALTH_EMERGENCY},
            )
            ticket = await self._handoff.start(
                uow=uow,
                conv=conv,
                caller=caller,
                decision=decision,
                now=now,
            )
            notice = (
                self._messages.handoff_in_business_hours
                if is_business_hours(now)
                else self._messages.handoff_out_of_hours
            )
            outbound = OutboundMessage(
                id=new_ulid(),
                conversation_id=conv.id.value,
                recipient_phone=conv.channel_user_phone,
                text=notice,
                ui_hint=None,
                created_at=now,
            )
            await uow.outbox.add(outbound)

        await self._scheduler.schedule_outbox_dispatch(outbound.id)
        return ticket.id
