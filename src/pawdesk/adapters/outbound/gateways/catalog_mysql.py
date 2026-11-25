"""Gateway de catálogo lendo produtos do MySQL."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pawdesk.adapters.outbound.persistence.mysql.mappers import product_to_domain
from pawdesk.adapters.outbound.persistence.mysql.models import ProductModel
from pawdesk.adapters.outbound.persistence.mysql.repositories._base import SessionSupport
from pawdesk.domain.entities.product import Product
from pawdesk.domain.value_objects.ids import Sku


class MySqlCatalogGateway(SessionSupport):
    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        super().__init__(session=session, session_factory=session_factory)

    async def get_by_sku(self, sku: Sku) -> Product | None:
        async with self._use_session() as session:
            row = (
                await session.execute(select(ProductModel).where(ProductModel.sku == sku.value))
            ).scalar_one_or_none()
            return product_to_domain(row) if row is not None else None
