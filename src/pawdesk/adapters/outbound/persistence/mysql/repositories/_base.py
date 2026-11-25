"""Helper compartilhado para acesso à sessão SQLAlchemy (UoW ou standalone)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SessionSupport:
    """Permite que o repositório opere dentro de um UnitOfWork ou com sessão própria."""

    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        if session is None and session_factory is None:
            raise ValueError("Informe session ou session_factory.")
        self._session = session
        self._session_factory = session_factory

    @asynccontextmanager
    async def _use_session(self, *, write: bool = False) -> AsyncIterator[AsyncSession]:
        if self._session is not None:
            yield self._session
            return
        assert self._session_factory is not None
        async with self._session_factory() as session:
            if write:
                async with session.begin():
                    yield session
            else:
                yield session
