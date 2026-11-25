"""Tasks periódicas (sweepers) para recuperação de mensagens pendentes no MySQL."""

from datetime import timedelta

from pawdesk.adapters.inbound.worker.celery_app import celery_app
from pawdesk.adapters.inbound.worker.deps import get_scope_factory
from pawdesk.shared.utils.asyncio_utils import run_sync


@celery_app.task(name="sweep_pending_inbound")
def sweep_pending_inbound() -> int:
    factory = get_scope_factory()

    async def _run() -> int:
        async with factory() as scoped:
            cutoff = scoped.clock.now() - timedelta(seconds=15)
            hashes = await scoped.conversations.list_conversations_with_stale_pending(cutoff)
            for user_hash in hashes:
                await scoped.scheduler.schedule_turn(user_hash, delay_ms=0)
            return len(hashes)

    return run_sync(_run)


@celery_app.task(name="sweep_pending_outbox")
def sweep_pending_outbox() -> int:
    factory = get_scope_factory()

    async def _run() -> int:
        async with factory() as scoped:
            due_ids = await scoped.outbox.list_due_pending(scoped.clock.now())
            for outbox_id in due_ids:
                await scoped.scheduler.schedule_outbox_dispatch(outbox_id)
            return len(due_ids)

    return run_sync(_run)
