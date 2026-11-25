"""Unit of Work transacional sobre SQLAlchemy AsyncSession."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pawdesk.adapters.outbound.persistence.mysql.repositories.audit import MySqlAuditLogRepository
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
from pawdesk.adapters.outbound.persistence.mysql.repositories.shipments import (
    MySqlShipmentRepository,
)
from pawdesk.application.ports.outbound.infra import SecretCipher


class MySqlUnitOfWork:
    """Agrupa os repositórios de uma transação atômica do turno."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cipher: SecretCipher,
    ) -> None:
        self._factory = session_factory
        self._cipher = cipher
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "MySqlUnitOfWork":
        self._session = self._factory()
        self.customers = MySqlCustomerRepository(session=self._session)
        self.orders = MySqlOrderRepository(session=self._session)
        self.shipments = MySqlShipmentRepository(session=self._session)
        self.conversations = MySqlConversationRepository(cipher=self._cipher, session=self._session)
        self.outbox = MySqlOutboxRepository(cipher=self._cipher, session=self._session)
        self.handoffs = MySqlHandoffRepository(session=self._session)
        self.audit_logs = MySqlAuditLogRepository(session=self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None:
                await self._session.rollback()
            else:
                await self._session.commit()
        finally:
            await self._session.close()
            self._session = None
