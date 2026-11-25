"""Entrypoint do Celery Worker & Beat com configuração e escopo registrados."""

from contextlib import asynccontextmanager

from pawdesk.adapters.inbound.worker.celery_app import celery_app
from pawdesk.adapters.inbound.worker.deps import register_scope_factory
from pawdesk.adapters.inbound.worker.tasks import (  # noqa: F401
    close_idle_conversations,
    process_turn,
    send_message,
    sweepers,
)
from pawdesk.adapters.outbound.observability.logging import configure_logging
from pawdesk.adapters.outbound.observability.otel import configure_otel
from pawdesk.bootstrap.container import Container
from pawdesk.bootstrap.settings import get_settings

_settings = get_settings()
configure_logging(_settings.log_level)
configure_otel("pawdesk-worker", _settings.otel_endpoint)

_container = Container(_settings)


@asynccontextmanager
async def _worker_scope():
    async with _container.scope(null_pool=True) as wired:
        yield wired


register_scope_factory(_worker_scope)

celery_app.conf.update(
    broker_url=_settings.redis_url,
    result_backend=_settings.redis_url,
    task_default_queue="default",
    task_routes={
        "process_turn": {"queue": "inbound"},
        "send_message": {"queue": "outbound"},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 300},
    beat_schedule={
        "sweep-pending-inbound": {"task": "sweep_pending_inbound", "schedule": 30.0},
        "sweep-pending-outbox": {"task": "sweep_pending_outbox", "schedule": 30.0},
        "close-idle-conversations": {"task": "close_idle_conversations", "schedule": 600.0},
    },
)

__all__ = ["celery_app"]
