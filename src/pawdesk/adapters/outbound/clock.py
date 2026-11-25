"""Implementação padrão do relógio em UTC."""

from datetime import UTC, datetime


class SystemClock:
    """Relógio de sistema em UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)
