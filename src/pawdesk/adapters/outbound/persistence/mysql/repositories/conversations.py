"""Repositório MySQL de conversas e mensagens (inbox transacional)."""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import asc, desc, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pawdesk.adapters.outbound.persistence.mysql.mappers import (
    conversation_to_domain,
    ensure_utc,
    inbound_message_to_domain,
    message_view_to_domain,
    to_mysql_naive_utc,
)
from pawdesk.adapters.outbound.persistence.mysql.models import ConversationModel, MessageModel
from pawdesk.adapters.outbound.persistence.mysql.repositories._base import SessionSupport
from pawdesk.application.dto.agent_io import AgentTurnResult
from pawdesk.application.dto.commands import IncomingMessage
from pawdesk.application.ports.outbound.infra import SecretCipher
from pawdesk.domain.constants import (
    ConversationStatus,
    MessageAuthor,
    MessageDirection,
    VerificationLevel,
)
from pawdesk.domain.entities.conversation import Conversation, InboundMessage, MessageView
from pawdesk.domain.value_objects.ids import ConversationId, CustomerId
from pawdesk.shared.utils.ids import new_ulid


class MySqlConversationRepository(SessionSupport):
    def __init__(
        self,
        *,
        cipher: SecretCipher,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        super().__init__(session=session, session_factory=session_factory)
        self._cipher = cipher

    async def add_inbound_if_new(
        self,
        msg: IncomingMessage,
        *,
        content_redacted: str,
        adk_session_id: str,
        idle_hours: int,
    ) -> bool:
        now_naive = to_mysql_naive_utc(msg.received_at)
        assert now_naive is not None
        try:
            async with self._use_session(write=True) as session:
                existing = (
                    await session.execute(
                        select(MessageModel.id).where(
                            MessageModel.provider_message_id == msg.provider_message_id
                        )
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    return False

                conv_row = (
                    await session.execute(
                        select(ConversationModel)
                        .where(
                            ConversationModel.channel_user_hash == msg.channel_user_hash,
                            ConversationModel.status != ConversationStatus.CLOSED.value,
                        )
                        .order_by(desc(ConversationModel.opened_at))
                        .limit(1)
                    )
                ).scalar_one_or_none()

                if conv_row is not None:
                    last_activity = ensure_utc(conv_row.last_activity_at)
                    received_utc = ensure_utc(msg.received_at)
                    if (
                        last_activity is not None
                        and received_utc is not None
                        and (received_utc - last_activity) > timedelta(hours=idle_hours)
                    ):
                        conv_row.status = ConversationStatus.CLOSED.value
                        conv_row.closed_at = now_naive
                        conv_row = None

                if conv_row is None:
                    conv_row = ConversationModel(
                        id=new_ulid(),
                        channel="whatsapp",
                        channel_user_hash=msg.channel_user_hash,
                        channel_user_enc=self._cipher.encrypt(msg.channel_user_phone),
                        customer_id=None,
                        status=ConversationStatus.ACTIVE.value,
                        verification_level=int(VerificationLevel.NONE),
                        verification_attempts=0,
                        blocked_until=None,
                        adk_session_id=adk_session_id,
                        opened_at=now_naive,
                        last_activity_at=now_naive,
                    )
                    session.add(conv_row)
                    await session.flush()
                else:
                    conv_row.last_activity_at = now_naive

                session.add(
                    MessageModel(
                        id=new_ulid(),
                        conversation_id=conv_row.id,
                        direction=MessageDirection.IN.value,
                        author=MessageAuthor.CUSTOMER.value,
                        provider_message_id=msg.provider_message_id,
                        content_redacted=content_redacted,
                        interactive_payload=msg.interactive_payload,
                        processed_at=None,
                        trace_id=msg.correlation_id,
                        created_at=now_naive,
                    )
                )
                return True
        except IntegrityError:
            return False

    async def get_by_id(self, conversation_id: ConversationId) -> Conversation | None:
        async with self._use_session() as session:
            row = (
                await session.execute(
                    select(ConversationModel).where(ConversationModel.id == conversation_id.value)
                )
            ).scalar_one_or_none()
            return conversation_to_domain(row, self._cipher) if row is not None else None

    async def get_active_by_user_hash(self, channel_user_hash: str) -> Conversation | None:
        async with self._use_session() as session:
            row = (
                await session.execute(
                    select(ConversationModel)
                    .where(
                        ConversationModel.channel_user_hash == channel_user_hash,
                        ConversationModel.status != ConversationStatus.CLOSED.value,
                    )
                    .order_by(desc(ConversationModel.opened_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            return conversation_to_domain(row, self._cipher) if row is not None else None

    async def list_pending_inbound(self, conversation_id: ConversationId) -> list[InboundMessage]:
        async with self._use_session() as session:
            rows = (
                (
                    await session.execute(
                        select(MessageModel)
                        .where(
                            MessageModel.conversation_id == conversation_id.value,
                            MessageModel.direction == MessageDirection.IN.value,
                            MessageModel.processed_at.is_(None),
                        )
                        .order_by(asc(MessageModel.created_at))
                    )
                )
                .scalars()
                .all()
            )
            return [inbound_message_to_domain(row) for row in rows]

    async def list_recent_messages(
        self, conversation_id: ConversationId, limit: int = 20
    ) -> list[MessageView]:
        async with self._use_session() as session:
            rows = (
                (
                    await session.execute(
                        select(MessageModel)
                        .where(MessageModel.conversation_id == conversation_id.value)
                        .order_by(desc(MessageModel.created_at))
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )
            return [message_view_to_domain(row) for row in reversed(rows)]

    async def mark_processed(self, messages: list[InboundMessage], processed_at: datetime) -> None:
        if not messages:
            return
        ids = [m.id for m in messages]
        async with self._use_session(write=True) as session:
            await session.execute(
                update(MessageModel)
                .where(MessageModel.id.in_(ids))
                .values(processed_at=to_mysql_naive_utc(processed_at))
            )

    async def append_agent_message(
        self,
        conv: Conversation,
        result: AgentTurnResult,
        *,
        cost_usd: Decimal,
        latency_ms: int,
        created_at: datetime,
    ) -> None:
        tokens_in = sum(u.input_tokens for u in result.usage)
        tokens_out = sum(u.output_tokens for u in result.usage)
        now_naive = to_mysql_naive_utc(created_at)
        assert now_naive is not None
        async with self._use_session(write=True) as session:
            session.add(
                MessageModel(
                    id=new_ulid(),
                    conversation_id=conv.id.value,
                    direction=MessageDirection.OUT.value,
                    author=MessageAuthor.AGENT.value,
                    provider_message_id=None,
                    content_redacted=result.reply_text,
                    interactive_payload=None,
                    processed_at=now_naive,
                    agent_name=result.agent_name,
                    tools_called=list(result.tools_called),
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    trace_id=result.trace_id,
                    created_at=now_naive,
                )
            )
            await session.execute(
                update(ConversationModel)
                .where(ConversationModel.id == conv.id.value)
                .values(last_activity_at=now_naive)
            )

    async def append_system_message(
        self,
        conv: Conversation,
        *,
        author: MessageAuthor,
        content_redacted: str,
        created_at: datetime,
    ) -> None:
        now_naive = to_mysql_naive_utc(created_at)
        assert now_naive is not None
        async with self._use_session(write=True) as session:
            session.add(
                MessageModel(
                    id=new_ulid(),
                    conversation_id=conv.id.value,
                    direction=MessageDirection.OUT.value,
                    author=author.value,
                    content_redacted=content_redacted,
                    processed_at=now_naive,
                    created_at=now_naive,
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
        async with self._use_session(write=True) as session:
            await session.execute(
                update(ConversationModel)
                .where(ConversationModel.id == conversation_id.value)
                .values(
                    customer_id=customer_id.value if customer_id else None,
                    verification_level=int(level),
                    verification_attempts=attempts,
                    blocked_until=to_mysql_naive_utc(blocked_until),
                )
            )

    async def update_status(
        self,
        conversation_id: ConversationId,
        status: ConversationStatus,
        *,
        closed_at: datetime | None = None,
    ) -> None:
        async with self._use_session(write=True) as session:
            await session.execute(
                update(ConversationModel)
                .where(ConversationModel.id == conversation_id.value)
                .values(
                    status=status.value,
                    closed_at=to_mysql_naive_utc(closed_at),
                )
            )

    async def list_conversations_with_stale_pending(
        self, cutoff: datetime, limit: int = 50
    ) -> list[str]:
        cutoff_naive = to_mysql_naive_utc(cutoff)
        async with self._use_session() as session:
            stmt = (
                select(ConversationModel.channel_user_hash)
                .join(MessageModel, MessageModel.conversation_id == ConversationModel.id)
                .where(
                    MessageModel.direction == MessageDirection.IN.value,
                    MessageModel.processed_at.is_(None),
                    MessageModel.created_at <= cutoff_naive,
                    ConversationModel.status != ConversationStatus.CLOSED.value,
                )
                .distinct()
                .limit(limit)
            )
            return list((await session.execute(stmt)).scalars().all())

    async def close_idle_conversations(self, cutoff: datetime, closed_at: datetime) -> int:
        cutoff_naive = to_mysql_naive_utc(cutoff)
        closed_naive = to_mysql_naive_utc(closed_at)
        async with self._use_session(write=True) as session:
            res = await session.execute(
                update(ConversationModel)
                .where(
                    ConversationModel.status == ConversationStatus.ACTIVE.value,
                    ConversationModel.last_activity_at < cutoff_naive,
                )
                .values(status=ConversationStatus.CLOSED.value, closed_at=closed_naive)
            )
            return int(res.rowcount or 0)  # type: ignore[attr-defined]

    async def anonymize_by_user_hash(self, channel_user_hash: str, anonymized_at: datetime) -> int:
        closed_naive = to_mysql_naive_utc(anonymized_at)
        async with self._use_session(write=True) as session:
            conv_ids = list(
                (
                    await session.execute(
                        select(ConversationModel.id).where(
                            ConversationModel.channel_user_hash == channel_user_hash
                        )
                    )
                )
                .scalars()
                .all()
            )
            if not conv_ids:
                return 0
            await session.execute(
                update(MessageModel)
                .where(MessageModel.conversation_id.in_(conv_ids))
                .values(content_redacted="[ANONIMIZADO LGPD]", interactive_payload=None)
            )
            await session.execute(
                update(ConversationModel)
                .where(ConversationModel.id.in_(conv_ids))
                .values(
                    channel_user_enc=b"",
                    customer_id=None,
                    status=ConversationStatus.CLOSED.value,
                    closed_at=closed_naive,
                )
            )
            return len(conv_ids)
