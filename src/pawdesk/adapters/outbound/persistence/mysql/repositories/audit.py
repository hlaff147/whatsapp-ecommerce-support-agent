"""Repositório MySQL da trilha de auditoria."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pawdesk.adapters.outbound.persistence.mysql.mappers import to_mysql_naive_utc
from pawdesk.adapters.outbound.persistence.mysql.models import AuditLogModel
from pawdesk.adapters.outbound.persistence.mysql.repositories._base import SessionSupport


class MySqlAuditLogRepository(SessionSupport):
    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        super().__init__(session=session, session_factory=session_factory)

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
        created_naive = to_mysql_naive_utc(created_at)
        assert created_naive is not None
        async with self._use_session(write=True) as session:
            session.add(
                AuditLogModel(
                    conversation_id=conversation_id,
                    actor=actor,
                    action=action,
                    tool=tool,
                    args_redacted=args_redacted,
                    result_status=result_status,
                    correlation_id=correlation_id,
                    created_at=created_naive,
                )
            )
