"""Webhook oficial do WhatsApp Cloud API (verificação + recepção com HMAC)."""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from pawdesk.adapters.inbound.http.deps import HttpDependencies
from pawdesk.adapters.inbound.http.schemas.whatsapp import WhatsAppWebhookPayload
from pawdesk.adapters.inbound.http.security import verify_meta_signature
from pawdesk.shared.utils.hashing import constant_time_equals

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])


def _deps(request: Request) -> HttpDependencies:
    deps: HttpDependencies = request.app.state.deps
    return deps


@router.get("")
async def verify(
    request: Request,
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> PlainTextResponse:
    deps = _deps(request)
    if mode == "subscribe" and constant_time_equals(token, deps.whatsapp_verify_token):
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verify token inválido.")


@router.post("", status_code=200)
async def receive(request: Request) -> dict[str, object]:
    deps = _deps(request)
    raw = await request.body()
    if not verify_meta_signature(
        raw, request.headers.get("X-Hub-Signature-256"), deps.whatsapp_app_secret
    ):
        raise HTTPException(status_code=401, detail="Assinatura inválida.")

    payload = WhatsAppWebhookPayload.model_validate_json(raw)
    accepted = 0
    for cmd in payload.to_incoming_messages(deps.pseudonym_secret):
        if await deps.receive_incoming_message.execute(cmd):
            accepted += 1
    return {"status": "ok", "accepted": accepted}
