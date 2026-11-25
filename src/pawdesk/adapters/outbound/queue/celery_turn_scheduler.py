"""Agendador de tarefas Celery por nome (sem importar adapters.inbound)."""

import asyncio

from celery import Celery

from pawdesk.shared.utils.ids import new_correlation_id


class CeleryTurnScheduler:
    """Implementa TurnScheduler publicando tasks por nome no broker Redis."""

    def __init__(self, broker_url: str) -> None:
        self._celery = Celery("pawdesk-producer", broker=broker_url)

    async def schedule_turn(self, channel_user_hash: str, delay_ms: int) -> None:
        countdown = max(0.0, delay_ms / 1000.0)
        correlation_id = new_correlation_id()
        await asyncio.to_thread(
            self._celery.send_task,
            "process_turn",
            args=[channel_user_hash, correlation_id],
            queue="inbound",
            countdown=countdown,
        )

    async def schedule_outbox_dispatch(self, outbox_id: str, delay_s: int = 0) -> None:
        await asyncio.to_thread(
            self._celery.send_task,
            "send_message",
            args=[outbox_id],
            queue="outbound",
            countdown=max(0, delay_s),
        )
