"""Entidades de Conversa e Mensagem."""

from dataclasses import dataclass
from datetime import datetime

from pawdesk.domain.constants import (
    ConversationStatus,
    MessageAuthor,
    MessageDirection,
    VerificationLevel,
)
from pawdesk.domain.value_objects.ids import ConversationId, CustomerId


@dataclass(frozen=True)
class Conversation:
    id: ConversationId
    channel: str
    channel_user_hash: str
    channel_user_phone: str
    customer_id: CustomerId | None
    status: ConversationStatus
    verification_level: VerificationLevel
    verification_attempts: int
    blocked_until: datetime | None
    adk_session_id: str
    opened_at: datetime
    last_activity_at: datetime
    closed_at: datetime | None = None


@dataclass(frozen=True)
class InboundMessage:
    id: str
    conversation_id: ConversationId
    provider_message_id: str
    text: str
    interactive_payload: str | None
    created_at: datetime
    processed_at: datetime | None = None


@dataclass(frozen=True)
class MessageView:
    direction: MessageDirection
    author: MessageAuthor
    content_redacted: str
    created_at: datetime
