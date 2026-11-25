"""Gateway HTTP para integração com helpdesk externo."""

import httpx

from pawdesk.application.dto.results import HandoffPackage
from pawdesk.application.errors import ExternalServiceUnavailable
from pawdesk.application.ports.outbound.gateways import HelpdeskTicketCreated


class HttpHelpdeskGateway:
    """Envia pacotes de handoff e mensagens subsequentes para um helpdesk via HTTP."""

    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = api_token
        self._client = http_client

    async def create_ticket(self, package: HandoffPackage) -> HelpdeskTicketCreated:
        payload = {
            "conversation_id": package.conversation_id,
            "summary": package.summary,
            "customer_first_name": package.customer_first_name,
            "verification_level": int(package.verification_level),
            "order_numbers": list(package.order_numbers),
            "actions_executed": list(package.actions_executed),
            "reason": package.reason.value,
            "priority": package.priority.value,
            "urgent": package.urgent,
            "sentiment": package.sentiment,
            "suggested_next_steps": package.suggested_next_steps,
        }
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            if self._client is not None:
                resp = await self._client.post(
                    f"{self._base_url}/tickets", json=payload, headers=headers
                )
            else:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(
                        f"{self._base_url}/tickets", json=payload, headers=headers
                    )
            resp.raise_for_status()
            data = resp.json()
            return HelpdeskTicketCreated(external_ticket_id=str(data["ticket_id"]))
        except httpx.HTTPError as exc:
            raise ExternalServiceUnavailable(f"Helpdesk HTTP error: {exc}") from exc

    async def forward_message(
        self,
        *,
        conversation_id: str,
        external_ticket_id: str | None,
        text_redacted: str,
    ) -> None:
        if not external_ticket_id:
            return
        headers = {"Authorization": f"Bearer {self._token}"}
        payload = {"conversation_id": conversation_id, "text": text_redacted}
        try:
            if self._client is not None:
                resp = await self._client.post(
                    f"{self._base_url}/tickets/{external_ticket_id}/messages",
                    json=payload,
                    headers=headers,
                )
            else:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(
                        f"{self._base_url}/tickets/{external_ticket_id}/messages",
                        json=payload,
                        headers=headers,
                    )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalServiceUnavailable(f"Helpdesk HTTP error: {exc}") from exc
