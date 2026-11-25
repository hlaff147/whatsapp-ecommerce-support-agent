"""Webhook do helpdesk para retomada da conversa após atendimento humano."""

from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Request

from pawdesk.adapters.inbound.http.deps import HttpDependencies
from pawdesk.adapters.inbound.http.schemas.helpdesk import HelpdeskResolutionRequest
from pawdesk.adapters.inbound.http.security import require_bearer_token
from pawdesk.application.dto.commands import HelpdeskResolutionCommand
from pawdesk.application.errors import NotFound
from pawdesk.shared.utils.ids import new_correlation_id

router = APIRouter(prefix="/webhooks/helpdesk", tags=["helpdesk"])


@router.post("/events")
async def receive_event(
    body: HelpdeskResolutionRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    deps: HttpDependencies = request.app.state.deps
    require_bearer_token(authorization, deps.helpdesk_webhook_secret)

    if body.event != "resolved":
        return {"status": "ignored", "event": body.event}

    cmd = HelpdeskResolutionCommand(
        conversation_id=body.conversation_id,
        helpdesk_ticket_id=body.ticket_id,
        resolution_note=body.resolution_note,
        resolved_at=datetime.now(UTC),
        correlation_id=new_correlation_id(),
    )
    try:
        await deps.resume_after_handoff.execute(cmd)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "resumed", "conversation_id": body.conversation_id}
