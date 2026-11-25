"""Repositório MySQL de pedidos."""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pawdesk.adapters.outbound.persistence.mysql.mappers import order_to_domain
from pawdesk.adapters.outbound.persistence.mysql.models import OrderModel
from pawdesk.adapters.outbound.persistence.mysql.repositories._base import SessionSupport
from pawdesk.domain.entities.order import Order
from pawdesk.domain.value_objects.ids import CustomerId, OrderNumber


class MySqlOrderRepository(SessionSupport):
    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        super().__init__(session=session, session_factory=session_factory)

    async def get_by_number(self, number: OrderNumber) -> Order | None:
        async with self._use_session() as session:
            stmt = select(OrderModel).where(OrderModel.number == number.value)
            row = (await session.execute(stmt)).scalar_one_or_none()
            return order_to_domain(row) if row is not None else None

    async def list_recent_by_customer(self, customer_id: CustomerId, limit: int) -> list[Order]:
        async with self._use_session() as session:
            stmt = (
                select(OrderModel)
                .where(OrderModel.customer_id == customer_id.value)
                .order_by(desc(OrderModel.placed_at))
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [order_to_domain(row) for row in rows]
