"""Repositório MySQL de entregas/rastreamentos."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pawdesk.adapters.outbound.persistence.mysql.mappers import shipment_to_domain
from pawdesk.adapters.outbound.persistence.mysql.models import ShipmentModel
from pawdesk.adapters.outbound.persistence.mysql.repositories._base import SessionSupport
from pawdesk.domain.entities.shipment import Shipment
from pawdesk.domain.value_objects.ids import OrderNumber


class MySqlShipmentRepository(SessionSupport):
    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        super().__init__(session=session, session_factory=session_factory)

    async def get_by_order_number(self, number: OrderNumber) -> Shipment | None:
        async with self._use_session() as session:
            stmt = select(ShipmentModel).where(ShipmentModel.order_number == number.value)
            row = (await session.execute(stmt)).scalar_one_or_none()
            return shipment_to_domain(row) if row is not None else None
