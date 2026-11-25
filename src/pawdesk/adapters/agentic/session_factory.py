"""Fábrica do serviço de sessões do ADK (InMemory ou MySQL DatabaseSessionService)."""

from google.adk.sessions import BaseSessionService, DatabaseSessionService, InMemorySessionService
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


def make_session_service(
    *,
    backend: str,
    adk_sessions_dsn: str | None = None,
    null_pool: bool = False,
) -> BaseSessionService:
    """Constrói o serviço de sessões ADK em memória ou persistido no schema pawdesk_adk."""
    if backend == "database" and adk_sessions_dsn:
        if null_pool:
            engine = create_async_engine(adk_sessions_dsn, poolclass=NullPool, pool_pre_ping=True)
            return DatabaseSessionService(db_engine=engine)
        return DatabaseSessionService(db_url=adk_sessions_dsn)
    return InMemorySessionService()
