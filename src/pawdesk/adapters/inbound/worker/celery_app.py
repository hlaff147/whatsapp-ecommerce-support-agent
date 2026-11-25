"""Instância Celery isolada (configurada pelo bootstrap/worker.py)."""

from celery import Celery

celery_app = Celery(
    "pawdesk",
    include=[
        "pawdesk.adapters.inbound.worker.tasks.process_turn",
        "pawdesk.adapters.inbound.worker.tasks.send_message",
        "pawdesk.adapters.inbound.worker.tasks.sweepers",
        "pawdesk.adapters.inbound.worker.tasks.close_idle_conversations",
    ],
)
