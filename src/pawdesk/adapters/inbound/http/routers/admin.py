"""Endpoints administrativos: métricas, auditoria de conversa e anonimização LGPD."""

from fastapi import APIRouter, Header, HTTPException, Request

from pawdesk.adapters.inbound.http.deps import HttpDependencies
from pawdesk.adapters.inbound.http.schemas.admin import AnonymizeRequest
from pawdesk.adapters.inbound.http.security import require_bearer_token
from pawdesk.domain.value_objects.ids import ConversationId
from pawdesk.shared.utils.ids import new_correlation_id

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics")
async def metrics(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    deps: HttpDependencies = request.app.state.deps
    require_bearer_token(authorization, deps.admin_api_token)
    return deps.telemetry.snapshot()


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    deps: HttpDependencies = request.app.state.deps
    require_bearer_token(authorization, deps.admin_api_token)
    conv = await deps.conversations.get_by_id(ConversationId(conversation_id))
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    messages = await deps.conversations.list_recent_messages(conv.id, limit=50)
    ticket = await deps.handoffs.get_open_by_conversation(conv.id)
    return {
        "conversation_id": conv.id.value,
        "status": conv.status.value,
        "verification_level": int(conv.verification_level),
        "user_hash": conv.channel_user_hash,
        "open_handoff_ticket_id": ticket.id if ticket else None,
        "messages": [
            {
                "direction": m.direction.value,
                "author": m.author.value,
                "content_redacted": m.content_redacted,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/lgpd/anonymize")
async def anonymize(
    body: AnonymizeRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    deps: HttpDependencies = request.app.state.deps
    require_bearer_token(authorization, deps.admin_api_token)
    if not body.phone and not body.channel_user_hash:
        raise HTTPException(status_code=400, detail="Informe phone ou channel_user_hash.")
    try:
        affected = await deps.anonymize_customer_data.execute(
            phone_e164=body.phone,
            channel_user_hash=body.channel_user_hash,
            correlation_id=new_correlation_id(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "anonymized", "conversations_affected": affected}
