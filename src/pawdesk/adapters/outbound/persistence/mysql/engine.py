"""Fábrica de AsyncEngine e AsyncSession para MySQL."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


def create_mysql_engine(dsn: str, *, null_pool: bool = False) -> AsyncEngine:
    """Cria AsyncEngine (usa NullPool para workers Celery por isolamento de event loop)."""
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if null_pool:
        kwargs["poolclass"] = NullPool
    return create_async_engine(dsn, **kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Cria fábrica de sessões assíncronas sem expirar objetos no commit."""
    return async_sessionmaker(engine, expire_on_commit=False)
