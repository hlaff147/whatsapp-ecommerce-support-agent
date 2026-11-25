"""Helper assíncrono de retentativa com backoff exponencial e jitter."""

import asyncio
import random
from collections.abc import Awaitable, Callable


async def retry_with_backoff[T](
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay_s: float = 0.2,
    max_delay_s: float = 2.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """Executa uma operação assíncrona com retentativa e jitter."""
    if attempts < 1:
        raise ValueError("attempts deve ser >= 1.")

    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except retry_on as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            delay = min(max_delay_s, base_delay_s * (2 ** (attempt - 1)))
            jitter = random.uniform(0.0, delay * 0.25)
            await asyncio.sleep(delay + jitter)

    assert last_exc is not None
    raise last_exc
