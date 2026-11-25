"""Repositório MySQL de clientes."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pawdesk.adapters.outbound.persistence.mysql.mappers import customer_to_domain
from pawdesk.adapters.outbound.persistence.mysql.models import CustomerModel
from pawdesk.adapters.outbound.persistence.mysql.repositories._base import SessionSupport
from pawdesk.domain.entities.customer import Customer
from pawdesk.domain.value_objects.ids import CustomerId
from pawdesk.domain.value_objects.phone import PhoneE164


class MySqlCustomerRepository(SessionSupport):
    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        super().__init__(session=session, session_factory=session_factory)

    async def get_by_id(self, customer_id: CustomerId) -> Customer | None:
        async with self._use_session() as session:
            stmt = select(CustomerModel).where(CustomerModel.id == customer_id.value)
            row = (await session.execute(stmt)).scalar_one_or_none()
            return customer_to_domain(row) if row is not None else None

    async def get_by_phone(self, phone: PhoneE164) -> Customer | None:
        async with self._use_session() as session:
            stmt = select(CustomerModel).where(CustomerModel.phone_e164 == phone.value)
            row = (await session.execute(stmt)).scalar_one_or_none()
            return customer_to_domain(row) if row is not None else None
