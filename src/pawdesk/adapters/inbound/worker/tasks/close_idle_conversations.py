"""Task periódica: encerrar conversas ociosas após janela de 24h (RN-16)."""

from pawdesk.adapters.inbound.worker.celery_app import celery_app
from pawdesk.adapters.inbound.worker.deps import get_scope_factory
from pawdesk.shared.utils.asyncio_utils import run_sync


@celery_app.task(name="close_idle_conversations")
def close_idle_conversations() -> int:
    factory = get_scope_factory()

    async def _run() -> int:
        async with factory() as scoped:
            return await scoped.conversation_service.close_idle()

    return run_sync(_run)
