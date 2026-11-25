"""Schemas de eventos do webhook de helpdesk."""

from pydantic import BaseModel


class HelpdeskResolutionRequest(BaseModel):
    conversation_id: str
    ticket_id: str | None = None
    event: str = "resolved"
    resolution_note: str | None = None
