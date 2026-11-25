"""Schemas de payload do webhook oficial WhatsApp Cloud API."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from pawdesk.application.dto.commands import IncomingMessage
from pawdesk.shared.utils.hashing import pseudonymize
from pawdesk.shared.utils.ids import new_correlation_id
from pawdesk.shared.utils.phone import to_e164


class _TextBody(BaseModel):
    body: str = ""


class _ButtonReply(BaseModel):
    id: str = ""
    title: str = ""


class _Interactive(BaseModel):
    type: str = ""
    button_reply: _ButtonReply | None = None
    list_reply: _ButtonReply | None = None


class _WaMessage(BaseModel):
    id: str
    from_: str = Field(alias="from")
    timestamp: str | None = None
    type: str = "text"
    text: _TextBody | None = None
    interactive: _Interactive | None = None


class _WaValue(BaseModel):
    messages: list[_WaMessage] = Field(default_factory=list)
    statuses: list[dict[str, object]] = Field(default_factory=list)


class _WaChange(BaseModel):
    value: _WaValue


class _WaEntry(BaseModel):
    changes: list[_WaChange] = Field(default_factory=list)


class WhatsAppWebhookPayload(BaseModel):
    object: str = "whatsapp_business_account"
    entry: list[_WaEntry] = Field(default_factory=list)

    def to_incoming_messages(self, pseudonym_secret: str) -> list[IncomingMessage]:
        commands: list[IncomingMessage] = []
        for entry in self.entry:
            for change in entry.changes:
                for msg in change.value.messages:
                    text = ""
                    interactive_payload: str | None = None
                    if msg.type == "text" and msg.text is not None:
                        text = msg.text.body
                    elif msg.type == "interactive" and msg.interactive is not None:
                        reply = msg.interactive.button_reply or msg.interactive.list_reply
                        if reply is not None:
                            interactive_payload = reply.id
                            text = reply.title or reply.id
                    else:
                        continue

                    try:
                        phone_e164 = to_e164(msg.from_)
                    except ValueError:
                        continue

                    received_at = datetime.now(UTC)
                    if msg.timestamp and msg.timestamp.isdigit():
                        received_at = datetime.fromtimestamp(int(msg.timestamp), tz=UTC)

                    commands.append(
                        IncomingMessage(
                            provider_message_id=msg.id,
                            channel_user_hash=pseudonymize(phone_e164, pseudonym_secret),
                            channel_user_phone=phone_e164,
                            text=text,
                            interactive_payload=interactive_payload,
                            received_at=received_at,
                            correlation_id=new_correlation_id(),
                        )
                    )
        return commands
