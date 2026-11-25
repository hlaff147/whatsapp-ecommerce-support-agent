"""Rate limiter simples por janela fixa no Redis."""

from redis.asyncio import Redis


class RedisRateLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def allow(self, key: str, limit: int, window_s: int) -> bool:
        current = await self._redis.incr(key)
        if current == 1:
            await self._redis.expire(key, window_s)
        return int(current) <= limit
