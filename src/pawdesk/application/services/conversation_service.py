"""Coordenação de ciclo de vida de conversas (fechamento por ociosidade e varredura)."""

from datetime import timedelta

from pawdesk.application.ports.outbound.infra import Clock
from pawdesk.application.ports.outbound.repositories import ConversationRepository
from pawdesk.shared.constants.limits import SESSION_IDLE_CLOSE_HOURS


class ConversationService:
    """Coordena rotinas de ciclo de vida das conversas."""

    def __init__(
        self,
        conversations: ConversationRepository,
        clock: Clock,
        idle_close_hours: int = SESSION_IDLE_CLOSE_HOURS,
    ) -> None:
        self._conversations = conversations
        self._clock = clock
        self._idle_close_hours = idle_close_hours

    async def close_idle(self) -> int:
        now = self._clock.now()
        cutoff = now - timedelta(hours=self._idle_close_hours)
        return await self._conversations.close_idle_conversations(cutoff=cutoff, closed_at=now)
