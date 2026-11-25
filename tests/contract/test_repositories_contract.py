"""Testes de contrato dos repositórios: MemoryDatabase vs SQLAlchemy async ORM."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pawdesk.adapters.outbound.persistence.memory.stores import (
    InMemoryConversationRepository,
    InMemoryCustomerRepository,
    InMemoryHandoffRepository,
    InMemoryOrderRepository,
    InMemoryOutboxRepository,
    MemoryDatabase,
)
from pawdesk.adapters.outbound.persistence.mysql.mappers import to_mysql_naive_utc
from pawdesk.adapters.outbound.persistence.mysql.models import (
    Base,
    CustomerModel,
    OrderItemModel,
    OrderModel,
)
from pawdesk.adapters.outbound.persistence.mysql.repositories.conversations import (
    MySqlConversationRepository,
)
from pawdesk.adapters.outbound.persistence.mysql.repositories.customers import (
    MySqlCustomerRepository,
)
from pawdesk.adapters.outbound.persistence.mysql.repositories.handoffs import (
    MySqlHandoffRepository,
)
from pawdesk.adapters.outbound.persistence.mysql.repositories.orders import MySqlOrderRepository
from pawdesk.adapters.outbound.persistence.mysql.repositories.outbox import MySqlOutboxRepository
from pawdesk.adapters.outbound.security.fernet_cipher import FernetSecretCipher
from pawdesk.application.dto.commands import IncomingMessage
from pawdesk.application.dto.results import OutboundMessage
from pawdesk.bootstrap.seed_data import build_seed_dataset
from pawdesk.domain.constants import ConversationStatus, OutboxStatus
from pawdesk.domain.value_objects.ids import OrderNumber
from pawdesk.domain.value_objects.phone import PhoneE164


@pytest.fixture(params=["memory", "sqlalchemy_sqlite"])
async def repo_bundle(
    request: pytest.FixtureRequest,
) -> AsyncIterator[dict[str, object]]:
    now = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)
    dataset = build_seed_dataset(now, "contract-secret")

    if request.param == "memory":
        db = MemoryDatabase()
        for c in dataset.customers:
            db.customers[c.id.value] = c
        for o in dataset.orders:
            db.orders[o.number.value] = o
        yield {
            "customers": InMemoryCustomerRepository(db),
            "orders": InMemoryOrderRepository(db),
            "conversations": InMemoryConversationRepository(db),
            "outbox": InMemoryOutboxRepository(db),
            "handoffs": InMemoryHandoffRepository(db),
            "now": now,
        }
        return

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )
    async with factory() as session, session.begin():
        for c in dataset.customers:
            session.add(
                CustomerModel(
                    id=c.id.value,
                    first_name=c.first_name,
                    phone_e164=c.phone.value,
                    cpf_last3=c.cpf_last3,
                    cpf_hash=c.cpf_hash,
                )
            )
        for o in dataset.orders:
            session.add(
                OrderModel(
                    number=o.number.value,
                    customer_id=o.customer_id.value,
                    status=o.status.value,
                    total_amount=o.total.amount,
                    currency=o.total.currency,
                    placed_at=to_mysql_naive_utc(o.placed_at),
                    delivered_at=to_mysql_naive_utc(o.delivered_at),
                    estimated_delivery_at=to_mysql_naive_utc(o.estimated_delivery_at),
                    items=[
                        OrderItemModel(
                            sku=i.sku,
                            name=i.name,
                            quantity=i.quantity,
                            unit_price=i.unit_price.amount,
                            category=i.category,
                            returnable=i.returnable,
                        )
                        for i in o.items
                    ],
                )
            )

    cipher = FernetSecretCipher("contract-cipher-key")
    try:
        yield {
            "customers": MySqlCustomerRepository(session_factory=factory),
            "orders": MySqlOrderRepository(session_factory=factory),
            "conversations": MySqlConversationRepository(cipher=cipher, session_factory=factory),
            "outbox": MySqlOutboxRepository(cipher=cipher, session_factory=factory),
            "handoffs": MySqlHandoffRepository(session_factory=factory),
            "now": now,
        }
    finally:
        await engine.dispose()


async def test_contract_customer_order_conversation_and_outbox(
    repo_bundle: dict[str, object],
) -> None:
    customers = repo_bundle["customers"]
    orders = repo_bundle["orders"]
    conversations = repo_bundle["conversations"]
    outbox = repo_bundle["outbox"]
    now: datetime = repo_bundle["now"]  # type: ignore[assignment]

    marina = await customers.get_by_phone(PhoneE164("+5511999990001"))  # type: ignore[attr-defined]
    assert marina is not None
    assert marina.first_name == "Marina"

    order = await orders.get_by_number(OrderNumber("PD-104822"))  # type: ignore[attr-defined]
    assert order is not None
    assert order.customer_id == marina.id

    msg = IncomingMessage(
        provider_message_id="wamid-contract-1",
        channel_user_hash="hash-marina-contract",
        channel_user_phone="+5511999990001",
        text="cadê meu pedido?",
        interactive_payload=None,
        received_at=now,
        correlation_id="corr-1",
    )
    assert (
        await conversations.add_inbound_if_new(  # type: ignore[attr-defined]
            msg,
            content_redacted="cadê meu pedido?",
            adk_session_id="01JCONTRACT000000000000001",
            idle_hours=24,
        )
        is True
    )
    # Duplicado -> False pela barreira de idempotência
    assert (
        await conversations.add_inbound_if_new(  # type: ignore[attr-defined]
            msg,
            content_redacted="cadê meu pedido?",
            adk_session_id="01JCONTRACT000000000000001",
            idle_hours=24,
        )
        is False
    )

    conv = await conversations.get_active_by_user_hash("hash-marina-contract")  # type: ignore[attr-defined]
    assert conv is not None
    assert conv.status == ConversationStatus.ACTIVE
    assert conv.channel_user_phone == "+5511999990001"

    pending = await conversations.list_pending_inbound(conv.id)  # type: ignore[attr-defined]
    assert len(pending) == 1
    await conversations.mark_processed(pending, now)  # type: ignore[attr-defined]
    assert await conversations.list_pending_inbound(conv.id) == []  # type: ignore[attr-defined]

    out_msg = OutboundMessage(
        id="01JOUTBOX00000000000000001",
        conversation_id=conv.id.value,
        recipient_phone="+5511999990001",
        text="Seu pedido está em rota!",
        ui_hint=None,
        created_at=now,
    )
    await outbox.add(out_msg)  # type: ignore[attr-defined]
    assert await outbox.get_status(out_msg.id) == OutboxStatus.PENDING  # type: ignore[attr-defined]
    await outbox.mark_sent(out_msg.id, "wamid.out.1", now)  # type: ignore[attr-defined]
    assert await outbox.get_status(out_msg.id) == OutboxStatus.SENT  # type: ignore[attr-defined]
