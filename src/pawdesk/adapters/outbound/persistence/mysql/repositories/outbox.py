"""Repositório MySQL de mensagens de saída (outbox transacional)."""

from datetime import datetime
from typing import cast

from sqlalchemy import asc, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pawdesk.adapters.outbound.persistence.mysql.mappers import ensure_utc, to_mysql_naive_utc
from pawdesk.adapters.outbound.persistence.mysql.models import OutboxMessageModel
from pawdesk.adapters.outbound.persistence.mysql.repositories._base import SessionSupport
from pawdesk.application.dto.results import OutboundMessage
from pawdesk.application.ports.outbound.infra import SecretCipher
from pawdesk.domain.constants import OutboxStatus
from pawdesk.domain.value_objects.ids import ConversationId


class MySqlOutboxRepository(SessionSupport):
    def __init__(
        self,
        *,
        cipher: SecretCipher,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        super().__init__(session=session, session_factory=session_factory)
        self._cipher = cipher

    async def add(self, msg: OutboundMessage) -> None:
        now_naive = to_mysql_naive_utc(msg.created_at)
        assert now_naive is not None
        payload: dict[str, object] = {
            "recipient_enc": self._cipher.encrypt(msg.recipient_phone).decode("ascii"),
            "text": msg.text,
            "ui_hint": msg.ui_hint,
        }
        async with self._use_session(write=True) as session:
            session.add(
                OutboxMessageModel(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    payload=payload,
                    status=OutboxStatus.PENDING.value,
                    attempts=0,
                    next_attempt_at=now_naive,
                    created_at=now_naive,
                )
            )

    async def get_by_id(self, outbox_id: str) -> OutboundMessage | None:
        async with self._use_session() as session:
            row = (
                await session.execute(
                    select(OutboxMessageModel).where(OutboxMessageModel.id == outbox_id)
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            return self._to_dto(row)

    async def get_status(self, outbox_id: str) -> OutboxStatus | None:
        async with self._use_session() as session:
            val = (
                await session.execute(
                    select(OutboxMessageModel.status).where(OutboxMessageModel.id == outbox_id)
                )
            ).scalar_one_or_none()
            return OutboxStatus(val) if val is not None else None

    async def mark_sent(self, outbox_id: str, provider_message_id: str, sent_at: datetime) -> None:
        async with self._use_session(write=True) as session:
            await session.execute(
                update(OutboxMessageModel)
                .where(OutboxMessageModel.id == outbox_id)
                .values(
                    status=OutboxStatus.SENT.value,
                    provider_message_id=provider_message_id,
                    sent_at=to_mysql_naive_utc(sent_at),
                )
            )

    async def mark_retry_or_failed(
        self,
        outbox_id: str,
        *,
        error: str,
        next_attempt_at: datetime | None,
        failed: bool,
    ) -> None:
        async with self._use_session(write=True) as session:
            row = (
                await session.execute(
                    select(OutboxMessageModel).where(OutboxMessageModel.id == outbox_id)
                )
            ).scalar_one_or_none()
            if row is None:
                return
            row.attempts += 1
            row.last_error = error[:255]
            if failed:
                row.status = OutboxStatus.FAILED.value
            elif next_attempt_at is not None:
                row.next_attempt_at = to_mysql_naive_utc(next_attempt_at) or row.next_attempt_at

    async def list_due_pending(self, now: datetime, limit: int = 50) -> list[str]:
        now_naive = to_mysql_naive_utc(now)
        async with self._use_session() as session:
            stmt = (
                select(OutboxMessageModel.id)
                .where(
                    OutboxMessageModel.status == OutboxStatus.PENDING.value,
                    OutboxMessageModel.next_attempt_at <= now_naive,
                )
                .order_by(asc(OutboxMessageModel.next_attempt_at))
                .limit(limit)
            )
            return list((await session.execute(stmt)).scalars().all())

    async def list_by_conversation(self, conversation_id: ConversationId) -> list[OutboundMessage]:
        async with self._use_session() as session:
            rows = (
                (
                    await session.execute(
                        select(OutboxMessageModel)
                        .where(OutboxMessageModel.conversation_id == conversation_id.value)
                        .order_by(asc(OutboxMessageModel.created_at))
                    )
                )
                .scalars()
                .all()
            )
            return [self._to_dto(row) for row in rows]

    def _to_dto(self, row: OutboxMessageModel) -> OutboundMessage:
        payload = row.payload
        recipient_enc = str(payload.get("recipient_enc", ""))
        recipient = self._cipher.decrypt(recipient_enc.encode("ascii")) if recipient_enc else ""
        ui_hint_raw = payload.get("ui_hint")
        ui_hint = cast(dict[str, object], ui_hint_raw) if isinstance(ui_hint_raw, dict) else None
        return OutboundMessage(
            id=row.id,
            conversation_id=row.conversation_id,
            recipient_phone=recipient,
            text=str(payload.get("text", "")),
            ui_hint=ui_hint,
            created_at=ensure_utc(row.created_at) or datetime.now(),
        )
