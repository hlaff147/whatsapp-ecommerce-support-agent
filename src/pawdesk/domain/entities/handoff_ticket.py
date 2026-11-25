"""Entidade de Ticket de Handoff Humano."""

from dataclasses import dataclass
from datetime import datetime

from pawdesk.domain.constants import HandoffPriority, HandoffReason, HandoffStatus
from pawdesk.domain.value_objects.ids import ConversationId


@dataclass(frozen=True)
class HandoffTicket:
    id: str
    conversation_id: ConversationId
    reason: HandoffReason
    priority: HandoffPriority
    urgent: bool
    summary: str
    helpdesk_ticket_id: str | None
    status: HandoffStatus
    created_at: datetime
    resolved_at: datetime | None = None
