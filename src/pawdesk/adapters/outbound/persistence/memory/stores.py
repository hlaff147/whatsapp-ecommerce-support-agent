"""Repositórios e Unit of Work em memória implementando as portas de saída."""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pawdesk.application.dto.agent_io import AgentTurnResult
from pawdesk.application.dto.commands import IncomingMessage
from pawdesk.application.dto.results import OutboundMessage
from pawdesk.domain.constants import (
    ConversationStatus,
    HandoffStatus,
    MessageAuthor,
    MessageDirection,
    OutboxStatus,
    VerificationLevel,
)
from pawdesk.domain.entities.conversation import Conversation, InboundMessage, MessageView
from pawdesk.domain.entities.customer import Customer
from pawdesk.domain.entities.handoff_ticket import HandoffTicket
from pawdesk.domain.entities.order import Order
from pawdesk.domain.entities.product import Product
from pawdesk.domain.entities.shipment import Shipment
from pawdesk.domain.value_objects.ids import ConversationId, CustomerId, OrderNumber, Sku
from pawdesk.domain.value_objects.phone import PhoneE164
from pawdesk.shared.utils.ids import new_ulid


@dataclass
class _StoredMessage:
    id: str
    conversation_id: ConversationId
    direction: MessageDirection
    author: MessageAuthor
    provider_message_id: str | None
    content_redacted: str
    interactive_payload: str | None
    created_at: datetime
    processed_at: datetime | None = None


@dataclass
class _StoredOutbox:
    dto: OutboundMessage
    status: OutboxStatus = OutboxStatus.PENDING
    attempts: int = 0
    next_attempt_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    provider_message_id: str | None = None
    last_error: str | None = None
    sent_at: datetime | None = None


@dataclass
class MemoryDatabase:
    """Estado compartilhado em memória para repositórios, gateways e UoW."""

    customers: dict[str, Customer] = field(default_factory=dict)
    orders: dict[str, Order] = field(default_factory=dict)
    shipments: dict[str, Shipment] = field(default_factory=dict)
    products: dict[str, Product] = field(default_factory=dict)
    conversations: dict[str, Conversation] = field(default_factory=dict)
    messages: list[_StoredMessage] = field(default_factory=list)
    seen_provider_ids: set[str] = field(default_factory=set)
    outbox: dict[str, _StoredOutbox] = field(default_factory=dict)
    handoffs: dict[str, HandoffTicket] = field(default_factory=dict)
    audit_logs: list[dict[str, object]] = field(default_factory=list)


class InMemoryCustomerRepository:
    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db

    async def get_by_id(self, customer_id: CustomerId) -> Customer | None:
        return self._db.customers.get(customer_id.value)

    async def get_by_phone(self, phone: PhoneE164) -> Customer | None:
        return next(
            (c for c in self._db.customers.values() if c.phone.value == phone.value),
            None,
        )


class InMemoryOrderRepository:
    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db

    async def get_by_number(self, number: OrderNumber) -> Order | None:
        return self._db.orders.get(number.value)

    async def list_recent_by_customer(self, customer_id: CustomerId, limit: int) -> list[Order]:
        matches = [o for o in self._db.orders.values() if o.customer_id == customer_id]
        matches.sort(key=lambda o: o.placed_at, reverse=True)
        return matches[:limit]


class InMemoryShipmentRepository:
    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db

    async def get_by_order_number(self, number: OrderNumber) -> Shipment | None:
        return self._db.shipments.get(number.value)


class InMemoryCatalogGateway:
    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db

    async def get_by_sku(self, sku: Sku) -> Product | None:
        return self._db.products.get(sku.value)


class InMemoryConversationRepository:
    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db

    async def add_inbound_if_new(
        self,
        msg: IncomingMessage,
        *,
        content_redacted: str,
        adk_session_id: str,
        idle_hours: int,
    ) -> bool:
        if msg.provider_message_id in self._db.seen_provider_ids:
            return False
        self._db.seen_provider_ids.add(msg.provider_message_id)

        conv = await self.get_active_by_user_hash(msg.channel_user_hash)
        if conv is not None and (msg.received_at - conv.last_activity_at) > timedelta(
            hours=idle_hours
        ):
            self._db.conversations[conv.id.value] = replace(
                conv, status=ConversationStatus.CLOSED, closed_at=msg.received_at
            )
            conv = None

        if conv is None:
            conv = Conversation(
                id=ConversationId(new_ulid()),
                channel="whatsapp",
                channel_user_hash=msg.channel_user_hash,
                channel_user_phone=msg.channel_user_phone,
                customer_id=None,
                status=ConversationStatus.ACTIVE,
                verification_level=VerificationLevel.NONE,
                verification_attempts=0,
                blocked_until=None,
                adk_session_id=adk_session_id,
                opened_at=msg.received_at,
                last_activity_at=msg.received_at,
            )
            self._db.conversations[conv.id.value] = conv
        else:
            self._db.conversations[conv.id.value] = replace(conv, last_activity_at=msg.received_at)

        self._db.messages.append(
            _StoredMessage(
                id=new_ulid(),
                conversation_id=conv.id,
                direction=MessageDirection.IN,
                author=MessageAuthor.CUSTOMER,
                provider_message_id=msg.provider_message_id,
                content_redacted=content_redacted,
                interactive_payload=msg.interactive_payload,
                created_at=msg.received_at,
            )
        )
        return True

    async def get_by_id(self, conversation_id: ConversationId) -> Conversation | None:
        return self._db.conversations.get(conversation_id.value)

    async def get_active_by_user_hash(self, channel_user_hash: str) -> Conversation | None:
        candidates = [
            c
            for c in self._db.conversations.values()
            if c.channel_user_hash == channel_user_hash and c.status != ConversationStatus.CLOSED
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda c: c.opened_at, reverse=True)
        return candidates[0]

    async def list_pending_inbound(self, conversation_id: ConversationId) -> list[InboundMessage]:
        pending = [
            InboundMessage(
                id=m.id,
                conversation_id=m.conversation_id,
                provider_message_id=m.provider_message_id or "",
                text=m.content_redacted,
                interactive_payload=m.interactive_payload,
                created_at=m.created_at,
                processed_at=m.processed_at,
            )
            for m in self._db.messages
            if m.conversation_id == conversation_id
            and m.direction == MessageDirection.IN
            and m.processed_at is None
        ]
        pending.sort(key=lambda m: m.created_at)
        return pending

    async def list_recent_messages(
        self, conversation_id: ConversationId, limit: int = 20
    ) -> list[MessageView]:
        msgs = [m for m in self._db.messages if m.conversation_id == conversation_id]
        msgs.sort(key=lambda m: m.created_at)
        return [
            MessageView(
                direction=m.direction,
                author=m.author,
                content_redacted=m.content_redacted,
                created_at=m.created_at,
            )
            for m in msgs[-limit:]
        ]

    async def mark_processed(self, messages: list[InboundMessage], processed_at: datetime) -> None:
        ids = {m.id for m in messages}
        for stored in self._db.messages:
            if stored.id in ids:
                stored.processed_at = processed_at

    async def append_agent_message(
        self,
        conv: Conversation,
        result: AgentTurnResult,
        *,
        cost_usd: Decimal,
        latency_ms: int,
        created_at: datetime,
    ) -> None:
        _ = (cost_usd, latency_ms)
        self._db.messages.append(
            _StoredMessage(
                id=new_ulid(),
                conversation_id=conv.id,
                direction=MessageDirection.OUT,
                author=MessageAuthor.AGENT,
                provider_message_id=None,
                content_redacted=result.reply_text,
                interactive_payload=None,
                created_at=created_at,
                processed_at=created_at,
            )
        )
        current = self._db.conversations.get(conv.id.value)
        if current is not None:
            self._db.conversations[conv.id.value] = replace(current, last_activity_at=created_at)

    async def append_system_message(
        self,
        conv: Conversation,
        *,
        author: MessageAuthor,
        content_redacted: str,
        created_at: datetime,
    ) -> None:
        self._db.messages.append(
            _StoredMessage(
                id=new_ulid(),
                conversation_id=conv.id,
                direction=MessageDirection.OUT,
                author=author,
                provider_message_id=None,
                content_redacted=content_redacted,
                interactive_payload=None,
                created_at=created_at,
                processed_at=created_at,
            )
        )

    async def update_identity(
        self,
        conversation_id: ConversationId,
        *,
        customer_id: CustomerId | None,
        level: VerificationLevel,
        attempts: int,
        blocked_until: datetime | None,
    ) -> None:
        current = self._db.conversations.get(conversation_id.value)
        if current is not None:
            self._db.conversations[conversation_id.value] = replace(
                current,
                customer_id=customer_id,
                verification_level=level,
                verification_attempts=attempts,
                blocked_until=blocked_until,
            )

    async def update_status(
        self,
        conversation_id: ConversationId,
        status: ConversationStatus,
        *,
        closed_at: datetime | None = None,
    ) -> None:
        current = self._db.conversations.get(conversation_id.value)
        if current is not None:
            self._db.conversations[conversation_id.value] = replace(
                current, status=status, closed_at=closed_at
            )

    async def list_conversations_with_stale_pending(
        self, cutoff: datetime, limit: int = 50
    ) -> list[str]:
        hashes: list[str] = []
        for msg in self._db.messages:
            if (
                msg.direction == MessageDirection.IN
                and msg.processed_at is None
                and msg.created_at <= cutoff
            ):
                conv = self._db.conversations.get(msg.conversation_id.value)
                if (
                    conv is not None
                    and conv.status != ConversationStatus.CLOSED
                    and conv.channel_user_hash not in hashes
                ):
                    hashes.append(conv.channel_user_hash)
                    if len(hashes) >= limit:
                        break
        return hashes

    async def close_idle_conversations(self, cutoff: datetime, closed_at: datetime) -> int:
        count = 0
        for cid, conv in list(self._db.conversations.items()):
            if conv.status == ConversationStatus.ACTIVE and conv.last_activity_at < cutoff:
                self._db.conversations[cid] = replace(
                    conv, status=ConversationStatus.CLOSED, closed_at=closed_at
                )
                count += 1
        return count

    async def anonymize_by_user_hash(self, channel_user_hash: str, anonymized_at: datetime) -> int:
        conv_ids = {
            cid
            for cid, c in self._db.conversations.items()
            if c.channel_user_hash == channel_user_hash
        }
        if not conv_ids:
            return 0
        for msg in self._db.messages:
            if msg.conversation_id.value in conv_ids:
                msg.content_redacted = "[ANONIMIZADO LGPD]"
                msg.interactive_payload = None
        for cid in conv_ids:
            conv = self._db.conversations[cid]
            self._db.conversations[cid] = replace(
                conv,
                channel_user_phone="[ANONIMIZADO]",
                customer_id=None,
                status=ConversationStatus.CLOSED,
                closed_at=anonymized_at,
            )
        return len(conv_ids)


class InMemoryOutboxRepository:
    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db

    async def add(self, msg: OutboundMessage) -> None:
        self._db.outbox[msg.id] = _StoredOutbox(dto=msg, next_attempt_at=msg.created_at)

    async def get_by_id(self, outbox_id: str) -> OutboundMessage | None:
        entry = self._db.outbox.get(outbox_id)
        return entry.dto if entry is not None else None

    async def get_status(self, outbox_id: str) -> OutboxStatus | None:
        entry = self._db.outbox.get(outbox_id)
        return entry.status if entry is not None else None

    async def mark_sent(self, outbox_id: str, provider_message_id: str, sent_at: datetime) -> None:
        entry = self._db.outbox.get(outbox_id)
        if entry is not None:
            entry.status = OutboxStatus.SENT
            entry.provider_message_id = provider_message_id
            entry.sent_at = sent_at

    async def mark_retry_or_failed(
        self,
        outbox_id: str,
        *,
        error: str,
        next_attempt_at: datetime | None,
        failed: bool,
    ) -> None:
        entry = self._db.outbox.get(outbox_id)
        if entry is not None:
            entry.attempts += 1
            entry.last_error = error[:255]
            if failed:
                entry.status = OutboxStatus.FAILED
            elif next_attempt_at is not None:
                entry.next_attempt_at = next_attempt_at

    async def list_due_pending(self, now: datetime, limit: int = 50) -> list[str]:
        due = [
            e.dto.id
            for e in self._db.outbox.values()
            if e.status == OutboxStatus.PENDING and e.next_attempt_at <= now
        ]
        return due[:limit]

    async def list_by_conversation(self, conversation_id: ConversationId) -> list[OutboundMessage]:
        items = [
            e.dto
            for e in self._db.outbox.values()
            if e.dto.conversation_id == conversation_id.value
        ]
        items.sort(key=lambda m: m.created_at)
        return items


class InMemoryHandoffRepository:
    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db

    async def create(self, ticket: HandoffTicket) -> None:
        self._db.handoffs[ticket.id] = ticket

    async def get_open_by_conversation(
        self, conversation_id: ConversationId
    ) -> HandoffTicket | None:
        open_tickets = [
            t
            for t in self._db.handoffs.values()
            if t.conversation_id == conversation_id and t.status != HandoffStatus.RESOLVED
        ]
        if not open_tickets:
            return None
        open_tickets.sort(key=lambda t: t.created_at, reverse=True)
        return open_tickets[0]

    async def update_status(
        self,
        ticket_id: str,
        status: HandoffStatus,
        *,
        resolved_at: datetime | None = None,
    ) -> None:
        current = self._db.handoffs.get(ticket_id)
        if current is not None:
            self._db.handoffs[ticket_id] = replace(current, status=status, resolved_at=resolved_at)


class InMemoryAuditLogRepository:
    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db

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
    ) -> None:
        self._db.audit_logs.append(
            {
                "conversation_id": conversation_id,
                "actor": actor,
                "action": action,
                "tool": tool,
                "args_redacted": args_redacted,
                "result_status": result_status,
                "correlation_id": correlation_id,
                "created_at": created_at,
            }
        )


class InMemoryUnitOfWork:
    def __init__(self, db: MemoryDatabase) -> None:
        self.customers = InMemoryCustomerRepository(db)
        self.orders = InMemoryOrderRepository(db)
        self.shipments = InMemoryShipmentRepository(db)
        self.conversations = InMemoryConversationRepository(db)
        self.outbox = InMemoryOutboxRepository(db)
        self.handoffs = InMemoryHandoffRepository(db)
        self.audit_logs = InMemoryAuditLogRepository(db)

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        return None
