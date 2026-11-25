"""Caso de uso: despachar mensagem pendente do outbox pelo canal configurado."""

from collections.abc import Callable
from datetime import timedelta

from pawdesk.application.ports.outbound.channel import MessageChannel
from pawdesk.application.ports.outbound.infra import Clock, UnitOfWork
from pawdesk.application.ports.outbound.telemetry import Telemetry
from pawdesk.domain.constants import OutboxStatus


class DispatchOutboxMessage:
    """Envia uma mensagem PENDING do outbox e atualiza seu estado (SENT ou FAILED/retry)."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], UnitOfWork],
        channel: MessageChannel,
        clock: Clock,
        telemetry: Telemetry,
        max_attempts: int = 5,
    ) -> None:
        self._uow_factory = uow_factory
        self._channel = channel
        self._clock = clock
        self._telemetry = telemetry
        self._max_attempts = max_attempts

    async def execute(self, outbox_id: str, attempt: int = 1) -> bool:
        async with self._uow_factory() as uow:
            status = await uow.outbox.get_status(outbox_id)
            if status != OutboxStatus.PENDING:
                return False
            outbound = await uow.outbox.get_by_id(outbox_id)
            if outbound is None:
                return False

        try:
            send_result = await self._channel.send_text(
                recipient_phone=outbound.recipient_phone,
                text=outbound.text,
                ui_hint=outbound.ui_hint,
            )
        except Exception as exc:
            now = self._clock.now()
            failed = attempt >= self._max_attempts
            next_attempt = None if failed else now + timedelta(seconds=min(60, 2**attempt))
            async with self._uow_factory() as uow:
                await uow.outbox.mark_retry_or_failed(
                    outbox_id,
                    error=str(exc)[:250],
                    next_attempt_at=next_attempt,
                    failed=failed,
                )
            self._telemetry.increment_outbox_event("failed" if failed else "retry")
            if not failed:
                raise
            return False

        async with self._uow_factory() as uow:
            await uow.outbox.mark_sent(
                outbox_id,
                provider_message_id=send_result.provider_message_id,
                sent_at=self._clock.now(),
            )
        self._telemetry.increment_outbox_event("sent")
        return True
