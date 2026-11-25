"""Modelos ORM SQLAlchemy 2 (separados das entidades de domínio)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

DateTimeMs = DateTime().with_variant(MYSQL_DATETIME(fsp=3), "mysql")


class Base(DeclarativeBase):
    """Base declarativa para o schema principal do PawDesk."""


# --- Tabelas do OMS / Catálogo simulado -------------------------------------


class CustomerModel(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    cpf_last3: Mapped[str] = mapped_column(String(3), nullable=False)
    cpf_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class OrderModel(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_customer_placed", "customer_id", "placed_at"),)

    number: Mapped[str] = mapped_column(String(20), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(26), ForeignKey("customers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    placed_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTimeMs, nullable=True)
    estimated_delivery_at: Mapped[datetime | None] = mapped_column(DateTimeMs, nullable=True)

    items: Mapped[list["OrderItemModel"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("orders.number", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    returnable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    order: Mapped[OrderModel] = relationship(back_populates="items")


class ShipmentModel(Base):
    __tablename__ = "shipments"

    order_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("orders.number", ondelete="CASCADE"), primary_key=True
    )
    carrier_name: Mapped[str] = mapped_column(String(80), nullable=False)
    tracking_code: Mapped[str] = mapped_column(String(60), nullable=False)
    tracking_url: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    estimated_delivery_at: Mapped[datetime | None] = mapped_column(DateTimeMs, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTimeMs, nullable=True)

    events: Mapped[list["ShipmentEventModel"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan", lazy="selectin"
    )


class ShipmentEventModel(Base):
    __tablename__ = "shipment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("shipments.order_number", ondelete="CASCADE"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    shipment: Mapped[ShipmentModel] = relationship(back_populates="events")


class ProductModel(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    species: Mapped[str] = mapped_column(String(30), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    in_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    weight_kg: Mapped[float] = mapped_column(nullable=False, default=1.0)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")


# --- Tabelas da aplicação PawDesk -------------------------------------------


class ConversationModel(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conv_user_status", "channel_user_hash", "status"),
        Index("ix_conv_activity", "status", "last_activity_at"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="whatsapp")
    channel_user_hash: Mapped[str] = mapped_column(String(24), nullable=False)
    channel_user_enc: Mapped[bytes] = mapped_column(LargeBinary(256), nullable=False)
    customer_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    verification_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTimeMs, nullable=True)
    adk_session_id: Mapped[str] = mapped_column(String(26), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTimeMs, nullable=True)


class MessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("provider_message_id", name="uq_provider_msg"),
        Index("ix_msg_conv_created", "conversation_id", "created_at"),
        Index("ix_msg_pending", "conversation_id", "direction", "processed_at"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("conversations.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    author: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_redacted: Mapped[str] = mapped_column(Text, nullable=False)
    interactive_payload: Mapped[str | None] = mapped_column(String(120), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTimeMs, nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tools_called: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)


class ReturnRequestModel(Base):
    __tablename__ = "return_requests"
    __table_args__ = (
        UniqueConstraint("action_id", name="uq_return_action"),
        Index("ix_return_order_item", "order_number", "item_sku"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    action_id: Mapped[str] = mapped_column(String(26), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(26), nullable=False)
    order_number: Mapped[str] = mapped_column(String(20), nullable=False)
    item_sku: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(30), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTimeMs, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)


class HandoffTicketModel(Base):
    __tablename__ = "handoff_tickets"
    __table_args__ = (Index("ix_handoff_conv", "conversation_id", "status"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(26), nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")
    urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    helpdesk_ticket_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTimeMs, nullable=True)


class OutboxMessageModel(Base):
    __tablename__ = "outbox_messages"
    __table_args__ = (Index("ix_outbox_pending", "status", "next_attempt_at"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(26), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTimeMs, nullable=True)


class AuditLogModel(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_conv", "conversation_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(26), nullable=False)
    actor: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    tool: Mapped[str | None] = mapped_column(String(60), nullable=True)
    args_redacted: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeMs, nullable=False)
