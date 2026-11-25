"""Comandos de entrada da camada de aplicação."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IncomingMessage:
    provider_message_id: str
    channel_user_hash: str
    channel_user_phone: str
    text: str
    interactive_payload: str | None
    received_at: datetime
    correlation_id: str


@dataclass(frozen=True)
class HelpdeskResolutionCommand:
    conversation_id: str
    helpdesk_ticket_id: str | None
    resolution_note: str | None
    resolved_at: datetime
    correlation_id: str
