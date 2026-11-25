"""Contrato de envio pelo canal de mensageria (WhatsApp Cloud API / Console)."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChannelSendResult:
    provider_message_id: str


class MessageChannel(Protocol):
    async def send_text(
        self,
        *,
        recipient_phone: str,
        text: str,
        ui_hint: dict[str, object] | None = None,
    ) -> ChannelSendResult: ...

    async def send_template(
        self,
        *,
        recipient_phone: str,
        template_name: str,
        parameters: list[str],
    ) -> ChannelSendResult: ...

    async def mark_as_read(self, provider_message_id: str) -> None: ...
