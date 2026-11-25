"""Adaptadores em memória para lock, agendamento, idempotência e rate limiter."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pawdesk.application.errors import ConversationBusy


class InMemoryConversationLock:
    def __init__(self) -> None:
        self._held: set[str] = set()

    @asynccontextmanager
    async def hold(self, key: str, ttl_s: int) -> AsyncIterator[None]:
        _ = ttl_s
        if key in self._held:
            raise ConversationBusy(f"Conversa ocupada: {key}")
        self._held.add(key)
        try:
            yield
        finally:
            self._held.discard(key)


class RecordingTurnScheduler:
    def __init__(self) -> None:
        self.scheduled_turns: list[tuple[str, int]] = []
        self.scheduled_outbox: list[tuple[str, int]] = []

    async def schedule_turn(self, channel_user_hash: str, delay_ms: int) -> None:
        self.scheduled_turns.append((channel_user_hash, delay_ms))

    async def schedule_outbox_dispatch(self, outbox_id: str, delay_s: int = 0) -> None:
        self.scheduled_outbox.append((outbox_id, delay_s))


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._keys: set[str] = set()

    async def claim(self, key: str, ttl_s: int) -> bool:
        _ = ttl_s
        if key in self._keys:
            return False
        self._keys.add(key)
        return True

    async def release(self, key: str) -> None:
        self._keys.discard(key)


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    async def allow(self, key: str, limit: int, window_s: int) -> bool:
        _ = window_s
        current = self._counts.get(key, 0) + 1
        self._counts[key] = current
        return current <= limit
