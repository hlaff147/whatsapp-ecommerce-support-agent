"""Canal de desenvolvimento/simulação que registra envios em log e memória."""

from dataclasses import dataclass
from threading import Lock

import structlog

from pawdesk.application.ports.outbound.channel import ChannelSendResult
from pawdesk.shared.utils.ids import new_ulid
from pawdesk.shared.utils.masking import mask_phone

log = structlog.get_logger("pawdesk.channel.console")


@dataclass(frozen=True)
class RecordedChannelMessage:
    provider_message_id: str
    recipient_phone: str
    text: str
    ui_hint: dict[str, object] | None


class ConsoleChannel:
    """Canal local para desenvolvimento e simulador sem chamadas externas à Meta API."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._sent: list[RecordedChannelMessage] = []

    async def send_text(
        self,
        *,
        recipient_phone: str,
        text: str,
        ui_hint: dict[str, object] | None = None,
    ) -> ChannelSendResult:
        msg_id = f"wamid.local.{new_ulid()}"
        with self._lock:
            self._sent.append(
                RecordedChannelMessage(
                    provider_message_id=msg_id,
                    recipient_phone=recipient_phone,
                    text=text,
                    ui_hint=ui_hint,
                )
            )
        log.info(
            "console_channel_send",
            recipient=mask_phone(recipient_phone),
            provider_message_id=msg_id,
            text=text,
            has_ui_hint=ui_hint is not None,
        )
        return ChannelSendResult(provider_message_id=msg_id)

    async def send_template(
        self,
        *,
        recipient_phone: str,
        template_name: str,
        parameters: list[str],
    ) -> ChannelSendResult:
        msg_id = f"wamid.local.tpl.{new_ulid()}"
        text = f"[TEMPLATE:{template_name}] " + ", ".join(parameters)
        with self._lock:
            self._sent.append(
                RecordedChannelMessage(
                    provider_message_id=msg_id,
                    recipient_phone=recipient_phone,
                    text=text,
                    ui_hint=None,
                )
            )
        return ChannelSendResult(provider_message_id=msg_id)

    async def mark_as_read(self, provider_message_id: str) -> None:
        log.debug("console_channel_read", provider_message_id=provider_message_id)

    def messages_for(self, recipient_phone: str) -> list[RecordedChannelMessage]:
        with self._lock:
            return [m for m in self._sent if m.recipient_phone == recipient_phone]
