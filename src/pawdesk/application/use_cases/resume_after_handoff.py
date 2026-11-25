"""Caso de uso: retomar atendimento pelo agente após encerramento humano no helpdesk."""

from collections.abc import Callable

from pawdesk.application.dto.commands import HelpdeskResolutionCommand
from pawdesk.application.errors import NotFound
from pawdesk.application.ports.outbound.infra import TurnScheduler, UnitOfWork
from pawdesk.application.services.handoff_service import HandoffService
from pawdesk.domain.value_objects.ids import ConversationId


class ResumeAfterHandoff:
    """Reativa o bot quando o helpdesk sinaliza resolução do ticket humano."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], UnitOfWork],
        handoff: HandoffService,
        scheduler: TurnScheduler,
    ) -> None:
        self._uow_factory = uow_factory
        self._handoff = handoff
        self._scheduler = scheduler

    async def execute(self, cmd: HelpdeskResolutionCommand) -> bool:
        outbound_id: str | None = None
        async with self._uow_factory() as uow:
            conv = await uow.conversations.get_by_id(ConversationId(cmd.conversation_id))
            if conv is None:
                raise NotFound("conversa")
            outbound = await self._handoff.resume(
                uow=uow,
                conv=conv,
                correlation_id=cmd.correlation_id,
                resolution_note=cmd.resolution_note,
            )
            if outbound is not None:
                outbound_id = outbound.id

        if outbound_id is not None:
            await self._scheduler.schedule_outbox_dispatch(outbound_id)
        return True
