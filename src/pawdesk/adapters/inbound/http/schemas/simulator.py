"""Schemas do simulador local de WhatsApp."""

from pydantic import BaseModel, Field


class SimulatorMessageRequest(BaseModel):
    phone: str
    text: str = ""
    interactive_payload: str | None = None
    provider_message_id: str | None = None
    burst: list[str] = Field(default_factory=list)
    sync: bool = True
