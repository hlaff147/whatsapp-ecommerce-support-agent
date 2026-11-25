"""Mappers bidirecionais entre modelos ORM e entidades de domínio."""

from datetime import UTC, datetime

from pawdesk.adapters.outbound.persistence.mysql.models import (
    ConversationModel,
    CustomerModel,
    HandoffTicketModel,
    MessageModel,
    OrderModel,
    ProductModel,
    ShipmentModel,
)
from pawdesk.application.ports.outbound.infra import SecretCipher
from pawdesk.domain.constants import (
    ConversationStatus,
    HandoffPriority,
    HandoffReason,
    HandoffStatus,
    MessageAuthor,
    MessageDirection,
    OrderStatus,
    ShipmentStatus,
    VerificationLevel,
)
from pawdesk.domain.entities.conversation import Conversation, InboundMessage, MessageView
from pawdesk.domain.entities.customer import Customer
from pawdesk.domain.entities.handoff_ticket import HandoffTicket
from pawdesk.domain.entities.order import Order, OrderItem
from pawdesk.domain.entities.product import Product
from pawdesk.domain.entities.shipment import Shipment, ShipmentEvent
from pawdesk.domain.value_objects.ids import ConversationId, CustomerId, OrderNumber
from pawdesk.domain.value_objects.money import Money
from pawdesk.domain.value_objects.phone import PhoneE164
from pawdesk.domain.value_objects.tracking_code import TrackingCode


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_mysql_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def customer_to_domain(row: CustomerModel) -> Customer:
    return Customer(
        id=CustomerId(row.id),
        first_name=row.first_name,
        phone=PhoneE164(row.phone_e164),
        cpf_last3=row.cpf_last3,
        cpf_hash=row.cpf_hash,
    )


def order_to_domain(row: OrderModel) -> Order:
    items = tuple(
        OrderItem(
            sku=item.sku,
            name=item.name,
            quantity=item.quantity,
            unit_price=Money(item.unit_price, row.currency),
            category=item.category,
            returnable=item.returnable,
        )
        for item in row.items
    )
    return Order(
        number=OrderNumber(row.number),
        customer_id=CustomerId(row.customer_id),
        status=OrderStatus(row.status),
        items=items,
        total=Money(row.total_amount, row.currency),
        placed_at=ensure_utc(row.placed_at) or datetime.now(UTC),
        delivered_at=ensure_utc(row.delivered_at),
        estimated_delivery_at=ensure_utc(row.estimated_delivery_at),
    )


def shipment_to_domain(row: ShipmentModel) -> Shipment:
    events = tuple(
        ShipmentEvent(
            occurred_at=ensure_utc(ev.occurred_at) or datetime.now(UTC),
            status=ev.status,
            location=ev.location,
            description=ev.description,
        )
        for ev in row.events
    )
    return Shipment(
        order_number=OrderNumber(row.order_number),
        carrier_name=row.carrier_name,
        tracking_code=TrackingCode(row.tracking_code),
        tracking_url=row.tracking_url,
        status=ShipmentStatus(row.status),
        estimated_delivery_at=ensure_utc(row.estimated_delivery_at),
        delivered_at=ensure_utc(row.delivered_at),
        events=events,
    )


def product_to_domain(row: ProductModel) -> Product:
    return Product(
        sku=row.sku,
        name=row.name,
        species=row.species,
        category=row.category,
        price=Money(row.price_amount),
        in_stock=row.in_stock,
        weight_kg=row.weight_kg,
        description=row.description,
    )


def conversation_to_domain(row: ConversationModel, cipher: SecretCipher) -> Conversation:
    phone_plain = "[ANONIMIZADO]"
    if row.channel_user_enc:
        try:
            phone_plain = cipher.decrypt(row.channel_user_enc)
        except Exception:
            phone_plain = "[INDISPONIVEL]"
    return Conversation(
        id=ConversationId(row.id),
        channel=row.channel,
        channel_user_hash=row.channel_user_hash,
        channel_user_phone=phone_plain,
        customer_id=CustomerId(row.customer_id) if row.customer_id else None,
        status=ConversationStatus(row.status),
        verification_level=VerificationLevel(row.verification_level),
        verification_attempts=row.verification_attempts,
        blocked_until=ensure_utc(row.blocked_until),
        adk_session_id=row.adk_session_id,
        opened_at=ensure_utc(row.opened_at) or datetime.now(UTC),
        last_activity_at=ensure_utc(row.last_activity_at) or datetime.now(UTC),
        closed_at=ensure_utc(row.closed_at),
    )


def inbound_message_to_domain(row: MessageModel) -> InboundMessage:
    return InboundMessage(
        id=row.id,
        conversation_id=ConversationId(row.conversation_id),
        provider_message_id=row.provider_message_id or "",
        text=row.content_redacted,
        interactive_payload=row.interactive_payload,
        created_at=ensure_utc(row.created_at) or datetime.now(UTC),
        processed_at=ensure_utc(row.processed_at),
    )


def message_view_to_domain(row: MessageModel) -> MessageView:
    return MessageView(
        direction=MessageDirection(row.direction),
        author=MessageAuthor(row.author),
        content_redacted=row.content_redacted,
        created_at=ensure_utc(row.created_at) or datetime.now(UTC),
    )


def handoff_to_domain(row: HandoffTicketModel) -> HandoffTicket:
    return HandoffTicket(
        id=row.id,
        conversation_id=ConversationId(row.conversation_id),
        reason=HandoffReason(row.reason),
        priority=HandoffPriority(row.priority),
        urgent=row.urgent,
        summary=row.summary,
        helpdesk_ticket_id=row.helpdesk_ticket_id,
        status=HandoffStatus(row.status),
        created_at=ensure_utc(row.created_at) or datetime.now(UTC),
        resolved_at=ensure_utc(row.resolved_at),
    )
