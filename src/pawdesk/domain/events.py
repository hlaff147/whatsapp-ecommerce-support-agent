"""Eventos de domínio imutáveis."""

from dataclasses import dataclass
from datetime import datetime

from pawdesk.domain.constants import HandoffReason, VerificationLevel
from pawdesk.domain.value_objects.ids import ConversationId, CustomerId


@dataclass(frozen=True)
class DomainEvent:
    """Evento base de domínio."""

    occurred_at: datetime


@dataclass(frozen=True)
class ConversationOpened(DomainEvent):
    conversation_id: ConversationId
    channel_user_hash: str


@dataclass(frozen=True)
class IdentityVerified(DomainEvent):
    conversation_id: ConversationId
    customer_id: CustomerId
    level: VerificationLevel


@dataclass(frozen=True)
class HandoffStarted(DomainEvent):
    conversation_id: ConversationId
    ticket_id: str
    reason: HandoffReason
    urgent: bool


@dataclass(frozen=True)
class HandoffResolved(DomainEvent):
    conversation_id: ConversationId
    ticket_id: str
