"""Relógio determinístico controlável para testes."""

from datetime import UTC, datetime, timedelta


class FakeClock:
    """Relógio fixo/avançável em memória (fuso UTC)."""

    def __init__(self, initial: datetime | None = None) -> None:
        self._now = initial or datetime(2026, 11, 24, 15, 0, tzinfo=UTC)  # Terça 12:00 BRT

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: int) -> datetime:
        self._now = self._now + timedelta(**kwargs)
        return self._now

    def set(self, dt: datetime) -> None:
        self._now = dt
