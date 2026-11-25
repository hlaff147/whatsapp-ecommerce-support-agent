"""Contratos de persistência (repositórios)."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from pawdesk.application.dto.agent_io import AgentTurnResult
from pawdesk.application.dto.commands import IncomingMessage
from pawdesk.application.dto.results import OutboundMessage
from pawdesk.domain.constants import (
    ConversationStatus,
    HandoffStatus,
    MessageAuthor,
    OutboxStatus,
    VerificationLevel,
)
from pawdesk.domain.entities.conversation import Conversation, InboundMessage, MessageView
from pawdesk.domain.entities.customer import Customer
from pawdesk.domain.entities.handoff_ticket import HandoffTicket
from pawdesk.domain.entities.order import Order
from pawdesk.domain.entities.shipment import Shipment
from pawdesk.domain.value_objects.ids import ConversationId, CustomerId, OrderNumber
from pawdesk.domain.value_objects.phone import PhoneE164


class CustomerRepository(Protocol):
    async def get_by_id(self, customer_id: CustomerId) -> Customer | None: ...
    async def get_by_phone(self, phone: PhoneE164) -> Customer | None: ...


class OrderRepository(Protocol):
    async def get_by_number(self, number: OrderNumber) -> Order | None: ...
    async def list_recent_by_customer(self, customer_id: CustomerId, limit: int) -> list[Order]: ...


class ShipmentRepository(Protocol):
    async def get_by_order_number(self, number: OrderNumber) -> Shipment | None: ...


class ConversationRepository(Protocol):
    async def add_inbound_if_new(
        self,
        msg: IncomingMessage,
        *,
        content_redacted: str,
        adk_session_id: str,
        idle_hours: int,
    ) -> bool: ...
    async def get_by_id(self, conversation_id: ConversationId) -> Conversation | None: ...
    async def get_active_by_user_hash(self, channel_user_hash: str) -> Conversation | None: ...
    async def list_pending_inbound(
        self, conversation_id: ConversationId
    ) -> list[InboundMessage]: ...
    async def list_recent_messages(
        self, conversation_id: ConversationId, limit: int = 20
    ) -> list[MessageView]: ...
    async def mark_processed(
        self, messages: list[InboundMessage], processed_at: datetime
    ) -> None: ...
    async def append_agent_message(
        self,
        conv: Conversation,
        result: AgentTurnResult,
        *,
        cost_usd: Decimal,
        latency_ms: int,
        created_at: datetime,
    ) -> None: ...
    async def append_system_message(
        self,
        conv: Conversation,
        *,
        author: MessageAuthor,
        content_redacted: str,
        created_at: datetime,
    ) -> None: ...
    async def update_identity(
        self,
        conversation_id: ConversationId,
        *,
        customer_id: CustomerId | None,
        level: VerificationLevel,
        attempts: int,
        blocked_until: datetime | None,
    ) -> None: ...
    async def update_status(
        self,
        conversation_id: ConversationId,
        status: ConversationStatus,
        *,
        closed_at: datetime | None = None,
    ) -> None: ...
    async def list_conversations_with_stale_pending(
        self, cutoff: datetime, limit: int = 50
    ) -> list[str]: ...
    async def close_idle_conversations(self, cutoff: datetime, closed_at: datetime) -> int: ...
    async def anonymize_by_user_hash(
        self, channel_user_hash: str, anonymized_at: datetime
    ) -> int: ...


class OutboxRepository(Protocol):
    async def add(self, msg: OutboundMessage) -> None: ...
    async def get_by_id(self, outbox_id: str) -> OutboundMessage | None: ...
    async def get_status(self, outbox_id: str) -> OutboxStatus | None: ...
    async def mark_sent(
        self, outbox_id: str, provider_message_id: str, sent_at: datetime
    ) -> None: ...
    async def mark_retry_or_failed(
        self,
        outbox_id: str,
        *,
        error: str,
        next_attempt_at: datetime | None,
        failed: bool,
    ) -> None: ...
    async def list_due_pending(self, now: datetime, limit: int = 50) -> list[str]: ...
    async def list_by_conversation(
        self, conversation_id: ConversationId
    ) -> list[OutboundMessage]: ...


class HandoffRepository(Protocol):
    async def create(self, ticket: HandoffTicket) -> None: ...
    async def get_open_by_conversation(
        self, conversation_id: ConversationId
    ) -> HandoffTicket | None: ...
    async def update_status(
        self,
        ticket_id: str,
        status: HandoffStatus,
        *,
        resolved_at: datetime | None = None,
    ) -> None: ...


class AuditLogRepository(Protocol):
    async def record(
        self,
        *,
        conversation_id: str,
        actor: str,
        action: str,
        tool: str | None,
        args_redacted: dict[str, object] | None,
        result_status: str | None,
        correlation_id: str | None,
        created_at: datetime,
    ) -> None: ...
