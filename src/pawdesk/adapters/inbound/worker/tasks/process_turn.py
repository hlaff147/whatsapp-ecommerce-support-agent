"""Task Celery: processar turno de conversa com lock, debounce e retry automático."""

from pawdesk.adapters.inbound.worker.celery_app import celery_app
from pawdesk.adapters.inbound.worker.deps import get_scope_factory
from pawdesk.application.errors import TransientError
from pawdesk.shared.utils.asyncio_utils import run_sync


@celery_app.task(
    name="process_turn",
    bind=True,
    acks_late=True,
    autoretry_for=(TransientError,),
    retry_backoff=2,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
    soft_time_limit=75,
    time_limit=90,
)
def process_turn(self, channel_user_hash: str, correlation_id: str) -> None:
    _ = self
    factory = get_scope_factory()

    async def _run() -> None:
        async with factory() as scoped:
            await scoped.process_conversation_turn.execute(channel_user_hash, correlation_id)

    run_sync(_run)
