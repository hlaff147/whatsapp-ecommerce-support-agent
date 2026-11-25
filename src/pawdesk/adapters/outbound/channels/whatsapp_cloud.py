"""Adaptador de produção para WhatsApp Cloud API (Meta Graph)."""

from typing import Any

import httpx

from pawdesk.application.errors import ExternalServiceUnavailable
from pawdesk.application.ports.outbound.channel import ChannelSendResult
from pawdesk.shared.constants.limits import WHATSAPP_MAX_TEXT_CHARS
from pawdesk.shared.utils.retry import retry_with_backoff
from pawdesk.shared.utils.text import truncate_for_whatsapp


class WhatsAppCloudChannel:
    """Envia mensagens de texto, botões interativos e templates via WhatsApp Cloud API."""

    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        api_version: str = "v21.0",
        base_url: str = "https://graph.facebook.com",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = access_token
        self._phone_number_id = phone_number_id
        self._endpoint = f"{base_url.rstrip('/')}/{api_version}/{phone_number_id}/messages"
        self._client = http_client

    async def send_text(
        self,
        *,
        recipient_phone: str,
        text: str,
        ui_hint: dict[str, object] | None = None,
    ) -> ChannelSendResult:
        safe_text = truncate_for_whatsapp(text, WHATSAPP_MAX_TEXT_CHARS)
        to_digits = recipient_phone.lstrip("+")

        payload: dict[str, Any]
        if ui_hint and ui_hint.get("kind") == "confirm_buttons":
            buttons = ui_hint.get("buttons", [])
            payload = {
                "messaging_product": "whatsapp",
                "to": to_digits,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": safe_text[:1024]},
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {"id": str(btn["id"]), "title": str(btn["title"])[:20]},
                            }
                            for btn in (buttons if isinstance(buttons, list) else [])[:3]
                        ]
                    },
                },
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": to_digits,
                "type": "text",
                "text": {"preview_url": False, "body": safe_text},
            }

        data = await self._post(payload)
        messages = data.get("messages") or [{}]
        provider_id = str(messages[0].get("id", ""))
        return ChannelSendResult(provider_message_id=provider_id)

    async def send_template(
        self,
        *,
        recipient_phone: str,
        template_name: str,
        parameters: list[str],
    ) -> ChannelSendResult:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": recipient_phone.lstrip("+"),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "pt_BR"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": p} for p in parameters],
                    }
                ],
            },
        }
        data = await self._post(payload)
        messages = data.get("messages") or [{}]
        return ChannelSendResult(provider_message_id=str(messages[0].get("id", "")))

    async def mark_as_read(self, provider_message_id: str) -> None:
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": provider_message_id,
        }
        await self._post(payload)

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        async def _send() -> dict[str, Any]:
            if self._client is not None:
                resp = await self._client.post(self._endpoint, json=payload, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(self._endpoint, json=payload, headers=headers)
            if resp.status_code >= 500 or resp.status_code == 429:
                raise ExternalServiceUnavailable(f"WhatsApp API HTTP {resp.status_code}")
            resp.raise_for_status()
            return dict(resp.json())

        try:
            return await retry_with_backoff(
                _send,
                attempts=3,
                retry_on=(httpx.HTTPError, ExternalServiceUnavailable),
            )
        except httpx.HTTPError as exc:
            raise ExternalServiceUnavailable(f"Erro na WhatsApp Cloud API: {exc}") from exc
