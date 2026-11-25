"""Task Celery: despachar mensagem do outbox para o canal configurado."""

from pawdesk.adapters.inbound.worker.celery_app import celery_app
from pawdesk.adapters.inbound.worker.deps import get_scope_factory
from pawdesk.application.errors import TransientError
from pawdesk.shared.utils.asyncio_utils import run_sync


@celery_app.task(
    name="send_message",
    bind=True,
    acks_late=True,
    autoretry_for=(TransientError,),
    retry_backoff=2,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
    soft_time_limit=30,
    time_limit=45,
)
def send_message(self, outbox_id: str) -> bool:
    attempt = int(self.request.retries or 0) + 1
    factory = get_scope_factory()

    async def _run() -> bool:
        async with factory() as scoped:
            return await scoped.dispatch_outbox_message.execute(outbox_id, attempt=attempt)

    return run_sync(_run)
