"""Contratos de infraestrutura (locks, agendamento, UoW, relógio e cifra)."""

from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol

from pawdesk.application.ports.outbound.repositories import (
    AuditLogRepository,
    ConversationRepository,
    CustomerRepository,
    HandoffRepository,
    OrderRepository,
    OutboxRepository,
    ShipmentRepository,
)


class ConversationLock(Protocol):
    def hold(self, key: str, ttl_s: int) -> AbstractAsyncContextManager[None]: ...


class TurnScheduler(Protocol):
    async def schedule_turn(self, channel_user_hash: str, delay_ms: int) -> None: ...
    async def schedule_outbox_dispatch(self, outbox_id: str, delay_s: int = 0) -> None: ...


class IdempotencyStore(Protocol):
    async def claim(self, key: str, ttl_s: int) -> bool: ...
    async def release(self, key: str) -> None: ...


class RateLimiter(Protocol):
    async def allow(self, key: str, limit: int, window_s: int) -> bool: ...


class UnitOfWork(Protocol):
    @property
    def customers(self) -> CustomerRepository: ...
    @property
    def orders(self) -> OrderRepository: ...
    @property
    def shipments(self) -> ShipmentRepository: ...
    @property
    def conversations(self) -> ConversationRepository: ...
    @property
    def outbox(self) -> OutboxRepository: ...
    @property
    def handoffs(self) -> HandoffRepository: ...
    @property
    def audit_logs(self) -> AuditLogRepository: ...

    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class SecretCipher(Protocol):
    def encrypt(self, plaintext: str) -> bytes: ...
    def decrypt(self, ciphertext: bytes) -> str: ...
