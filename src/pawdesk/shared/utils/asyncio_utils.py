"""Ponte síncrono -> assíncrono para execução isolada em tasks Celery."""

import asyncio
from collections.abc import Awaitable, Callable


def run_sync[T](factory: Callable[[], Awaitable[T]]) -> T:
    """Executa uma corrotina em um event loop dedicado por invocação."""

    async def _runner() -> T:
        return await factory()

    return asyncio.run(_runner())
