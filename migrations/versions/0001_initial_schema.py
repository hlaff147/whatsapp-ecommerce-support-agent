"""Schema inicial do PawDesk (OMS simulado + tabelas da aplicação).

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False, unique=True),
        sa.Column("cpf_last3", sa.String(length=3), nullable=False),
        sa.Column("cpf_hash", sa.String(length=64), nullable=False),
    )

    op.create_table(
        "orders",
        sa.Column("number", sa.String(length=20), primary_key=True),
        sa.Column(
            "customer_id", sa.String(length=26), sa.ForeignKey("customers.id"), nullable=False
        ),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("placed_at", sa.DateTime(3), nullable=False),
        sa.Column("delivered_at", sa.DateTime(3), nullable=True),
        sa.Column("estimated_delivery_at", sa.DateTime(3), nullable=True),
    )
    op.create_index("ix_orders_customer_placed", "orders", ["customer_id", "placed_at"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "order_number",
            sa.String(length=20),
            sa.ForeignKey("orders.number", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("returnable", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "shipments",
        sa.Column(
            "order_number",
            sa.String(length=20),
            sa.ForeignKey("orders.number", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("carrier_name", sa.String(length=80), nullable=False),
        sa.Column("tracking_code", sa.String(length=60), nullable=False),
        sa.Column("tracking_url", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("estimated_delivery_at", sa.DateTime(3), nullable=True),
        sa.Column("delivered_at", sa.DateTime(3), nullable=True),
    )

    op.create_table(
        "shipment_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "order_number",
            sa.String(length=20),
            sa.ForeignKey("shipments.order_number", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(3), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
    )

    op.create_table(
        "products",
        sa.Column("sku", sa.String(length=40), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("species", sa.String(length=30), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("price_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("in_stock", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("weight_kg", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="whatsapp"),
        sa.Column("channel_user_hash", sa.String(length=24), nullable=False),
        sa.Column("channel_user_enc", sa.LargeBinary(256), nullable=False),
        sa.Column("customer_id", sa.String(length=26), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("verification_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verification_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_until", sa.DateTime(3), nullable=True),
        sa.Column("adk_session_id", sa.String(length=26), nullable=False),
        sa.Column("opened_at", sa.DateTime(3), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(3), nullable=False),
        sa.Column("closed_at", sa.DateTime(3), nullable=True),
    )
    op.create_index("ix_conv_user_status", "conversations", ["channel_user_hash", "status"])
    op.create_index("ix_conv_activity", "conversations", ["status", "last_activity_at"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(length=26),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("author", sa.String(length=20), nullable=False),
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
        sa.Column("content_redacted", sa.Text(), nullable=False),
        sa.Column("interactive_payload", sa.String(length=120), nullable=True),
        sa.Column("processed_at", sa.DateTime(3), nullable=True),
        sa.Column("agent_name", sa.String(length=40), nullable=True),
        sa.Column("tools_called", sa.JSON(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(3), nullable=False),
        sa.UniqueConstraint("provider_message_id", name="uq_provider_msg"),
    )
    op.create_index("ix_msg_conv_created", "messages", ["conversation_id", "created_at"])
    op.create_index("ix_msg_pending", "messages", ["conversation_id", "direction", "processed_at"])

    op.create_table(
        "return_requests",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("action_id", sa.String(length=26), nullable=False),
        sa.Column("conversation_id", sa.String(length=26), nullable=False),
        sa.Column("order_number", sa.String(length=20), nullable=False),
        sa.Column("item_sku", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("details", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("protocol", sa.String(length=30), nullable=True),
        sa.Column("expires_at", sa.DateTime(3), nullable=True),
        sa.Column("created_at", sa.DateTime(3), nullable=False),
        sa.Column("updated_at", sa.DateTime(3), nullable=False),
        sa.UniqueConstraint("action_id", name="uq_return_action"),
    )
    op.create_index("ix_return_order_item", "return_requests", ["order_number", "item_sku"])

    op.create_table(
        "handoff_tickets",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("conversation_id", sa.String(length=26), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="NORMAL"),
        sa.Column("urgent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("helpdesk_ticket_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(3), nullable=False),
        sa.Column("resolved_at", sa.DateTime(3), nullable=True),
    )
    op.create_index("ix_handoff_conv", "handoff_tickets", ["conversation_id", "status"])

    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("conversation_id", sa.String(length=26), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(3), nullable=False),
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
        sa.Column("last_error", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(3), nullable=False),
        sa.Column("sent_at", sa.DateTime(3), nullable=True),
    )
    op.create_index("ix_outbox_pending", "outbox_messages", ["status", "next_attempt_at"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.String(length=26), nullable=False),
        sa.Column("actor", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("tool", sa.String(length=60), nullable=True),
        sa.Column("args_redacted", sa.JSON(), nullable=True),
        sa.Column("result_status", sa.String(length=20), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(3), nullable=False),
    )
    op.create_index("ix_audit_conv", "audit_log", ["conversation_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("outbox_messages")
    op.drop_table("handoff_tickets")
    op.drop_table("return_requests")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("products")
    op.drop_table("shipment_events")
    op.drop_table("shipments")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("customers")
