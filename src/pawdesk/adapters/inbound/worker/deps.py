"""Contratos de escopo por execução para tasks Celery (injetados pelo bootstrap)."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from pawdesk.application.ports.outbound.infra import Clock, TurnScheduler
from pawdesk.application.ports.outbound.repositories import (
    ConversationRepository,
    OutboxRepository,
)
from pawdesk.application.services.conversation_service import ConversationService
from pawdesk.application.use_cases.dispatch_outbox_message import DispatchOutboxMessage
from pawdesk.application.use_cases.process_conversation_turn import ProcessConversationTurn


class WorkerScope(Protocol):
    process_conversation_turn: ProcessConversationTurn
    dispatch_outbox_message: DispatchOutboxMessage
    conversations: ConversationRepository
    outbox: OutboxRepository
    scheduler: TurnScheduler
    conversation_service: ConversationService
    clock: Clock


ScopeFactory = Callable[[], AbstractAsyncContextManager[WorkerScope]]

_scope_factory: ScopeFactory | None = None


def register_scope_factory(factory: ScopeFactory) -> None:
    global _scope_factory
    _scope_factory = factory


def get_scope_factory() -> ScopeFactory:
    if _scope_factory is None:
        raise RuntimeError(
            "Worker scope factory não registrada. Inicie o Celery via pawdesk.bootstrap.worker."
        )
    return _scope_factory
