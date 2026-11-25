"""Repositório MySQL de tickets de handoff humano."""

from datetime import datetime

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pawdesk.adapters.outbound.persistence.mysql.mappers import (
    handoff_to_domain,
    to_mysql_naive_utc,
)
from pawdesk.adapters.outbound.persistence.mysql.models import HandoffTicketModel
from pawdesk.adapters.outbound.persistence.mysql.repositories._base import SessionSupport
from pawdesk.domain.constants import HandoffStatus
from pawdesk.domain.entities.handoff_ticket import HandoffTicket
from pawdesk.domain.value_objects.ids import ConversationId


class MySqlHandoffRepository(SessionSupport):
    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        super().__init__(session=session, session_factory=session_factory)

    async def create(self, ticket: HandoffTicket) -> None:
        created_naive = to_mysql_naive_utc(ticket.created_at)
        assert created_naive is not None
        async with self._use_session(write=True) as session:
            session.add(
                HandoffTicketModel(
                    id=ticket.id,
                    conversation_id=ticket.conversation_id.value,
                    reason=ticket.reason.value,
                    priority=ticket.priority.value,
                    urgent=ticket.urgent,
                    summary=ticket.summary,
                    helpdesk_ticket_id=ticket.helpdesk_ticket_id,
                    status=ticket.status.value,
                    created_at=created_naive,
                    resolved_at=to_mysql_naive_utc(ticket.resolved_at),
                )
            )

    async def get_open_by_conversation(
        self, conversation_id: ConversationId
    ) -> HandoffTicket | None:
        async with self._use_session() as session:
            row = (
                await session.execute(
                    select(HandoffTicketModel)
                    .where(
                        HandoffTicketModel.conversation_id == conversation_id.value,
                        HandoffTicketModel.status != HandoffStatus.RESOLVED.value,
                    )
                    .order_by(desc(HandoffTicketModel.created_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            return handoff_to_domain(row) if row is not None else None

    async def update_status(
        self,
        ticket_id: str,
        status: HandoffStatus,
        *,
        resolved_at: datetime | None = None,
    ) -> None:
        async with self._use_session(write=True) as session:
            await session.execute(
                update(HandoffTicketModel)
                .where(HandoffTicketModel.id == ticket_id)
                .values(status=status.value, resolved_at=to_mysql_naive_utc(resolved_at))
            )
