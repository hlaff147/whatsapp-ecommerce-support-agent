"""Lock distribuído por conversa sobre Redis."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pawdesk.application.errors import ConversationBusy
from redis.asyncio import Redis

_RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class RedisConversationLock:
    """Garante exclusão mútua por conversa usando SET NX EX e liberação atômica por Lua."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @asynccontextmanager
    async def hold(self, key: str, ttl_s: int) -> AsyncIterator[None]:
        token = uuid.uuid4().hex
        acquired = await self._redis.set(key, token, ex=ttl_s, nx=True)
        if not acquired:
            raise ConversationBusy(f"Conversa ocupada: {key}")
        try:
            yield
        finally:
            await self._redis.eval(_RELEASE_LUA, 1, key, token)
