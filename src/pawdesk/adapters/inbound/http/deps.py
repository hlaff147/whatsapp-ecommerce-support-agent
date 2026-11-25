"""Protocolo e contêiner de dependências injetadas pelo composition root na API HTTP."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pawdesk.application.ports.outbound.repositories import (
    ConversationRepository,
    HandoffRepository,
    OutboxRepository,
)
from pawdesk.application.ports.outbound.telemetry import Telemetry
from pawdesk.application.use_cases.anonymize_customer_data import AnonymizeCustomerData
from pawdesk.application.use_cases.dispatch_outbox_message import DispatchOutboxMessage
from pawdesk.application.use_cases.process_conversation_turn import ProcessConversationTurn
from pawdesk.application.use_cases.receive_incoming_message import ReceiveIncomingMessage
from pawdesk.application.use_cases.resume_after_handoff import ResumeAfterHandoff


@dataclass(frozen=True)
class HttpDependencies:
    receive_incoming_message: ReceiveIncomingMessage
    process_conversation_turn: ProcessConversationTurn
    dispatch_outbox_message: DispatchOutboxMessage
    resume_after_handoff: ResumeAfterHandoff
    anonymize_customer_data: AnonymizeCustomerData
    conversations: ConversationRepository
    outbox: OutboxRepository
    handoffs: HandoffRepository
    telemetry: Telemetry
    health_check: Callable[[], Awaitable[dict[str, bool]]]
    whatsapp_verify_token: str
    whatsapp_app_secret: str
    admin_api_token: str
    helpdesk_webhook_secret: str
    pseudonym_secret: str
    enable_simulator: bool = False
    simulator_inbox_reader: Callable[[str], list[dict[str, object]]] | None = None
    simulator_tickets_reader: Callable[[], list[dict[str, object]]] | None = None
