"""Caso de uso: receber mensagem do webhook, garantir idempotência e agendar turno."""

from pawdesk.application.dto.commands import IncomingMessage
from pawdesk.application.ports.outbound.infra import RateLimiter, TurnScheduler
from pawdesk.application.ports.outbound.repositories import ConversationRepository
from pawdesk.application.services.pii_redaction_service import PiiRedactionService
from pawdesk.shared.constants.limits import (
    DEBOUNCE_WINDOW_MS,
    RATE_LIMIT_MAX_MESSAGES,
    RATE_LIMIT_WINDOW_S,
    SESSION_IDLE_CLOSE_HOURS,
)
from pawdesk.shared.utils.ids import new_ulid


class ReceiveIncomingMessage:
    """Grava mensagem no inbox transacional (UNIQUE provider_message_id) e agenda turno."""

    def __init__(
        self,
        *,
        conversations: ConversationRepository,
        scheduler: TurnScheduler,
        redaction: PiiRedactionService,
        rate_limiter: RateLimiter | None = None,
        debounce_window_ms: int = DEBOUNCE_WINDOW_MS,
        idle_hours: int = SESSION_IDLE_CLOSE_HOURS,
    ) -> None:
        self._conversations = conversations
        self._scheduler = scheduler
        self._redaction = redaction
        self._rate_limiter = rate_limiter
        self._debounce_ms = debounce_window_ms
        self._idle_hours = idle_hours

    async def execute(self, cmd: IncomingMessage) -> bool:
        if self._rate_limiter is not None:
            allowed = await self._rate_limiter.allow(
                f"rl:{cmd.channel_user_hash}",
                limit=RATE_LIMIT_MAX_MESSAGES,
                window_s=RATE_LIMIT_WINDOW_S,
            )
            if not allowed:
                return False

        redacted = self._redaction.redact_text(cmd.text)
        inserted = await self._conversations.add_inbound_if_new(
            cmd,
            content_redacted=redacted,
            adk_session_id=new_ulid(),
            idle_hours=self._idle_hours,
        )
        if not inserted:
            return False

        await self._scheduler.schedule_turn(cmd.channel_user_hash, delay_ms=self._debounce_ms)
        return True
