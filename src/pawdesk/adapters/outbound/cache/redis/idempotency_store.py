"""Store rápido de idempotência no Redis (complementar ao UNIQUE no MySQL)."""

from redis.asyncio import Redis


class RedisIdempotencyStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def claim(self, key: str, ttl_s: int) -> bool:
        return bool(await self._redis.set(f"idem:{key}", "1", ex=ttl_s, nx=True))

    async def release(self, key: str) -> None:
        await self._redis.delete(f"idem:{key}")
