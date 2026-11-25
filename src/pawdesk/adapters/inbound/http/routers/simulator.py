"""Simulador local de WhatsApp e helpdesk (ativo apenas em env local/test)."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from pawdesk.adapters.inbound.http.deps import HttpDependencies
from pawdesk.adapters.inbound.http.schemas.simulator import SimulatorMessageRequest
from pawdesk.application.dto.commands import HelpdeskResolutionCommand, IncomingMessage
from pawdesk.application.errors import NotFound
from pawdesk.shared.utils.hashing import pseudonymize
from pawdesk.shared.utils.ids import new_correlation_id, new_ulid
from pawdesk.shared.utils.phone import to_e164

router = APIRouter(prefix="/simulator", tags=["simulator"])


@router.post("/whatsapp/messages")
async def simulate_inbound(
    body: SimulatorMessageRequest,
    request: Request,
) -> dict[str, object]:
    deps: HttpDependencies = request.app.state.deps
    if not deps.enable_simulator:
        raise HTTPException(status_code=404, detail="Simulador desabilitado.")

    try:
        phone = to_e164(body.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user_hash = pseudonymize(phone, deps.pseudonym_secret)
    texts = body.burst if body.burst else ([body.text] if body.text else [])
    if not texts and body.interactive_payload:
        texts = [body.interactive_payload]
    if not texts:
        raise HTTPException(status_code=400, detail="Informe text, burst ou interactive_payload.")

    accepted = 0
    for idx, txt in enumerate(texts):
        msg_id = (
            body.provider_message_id
            if (body.provider_message_id and idx == 0)
            else f"wamid.sim.{new_ulid()}"
        )
        cmd = IncomingMessage(
            provider_message_id=msg_id,
            channel_user_hash=user_hash,
            channel_user_phone=phone,
            text=txt,
            interactive_payload=body.interactive_payload if idx == len(texts) - 1 else None,
            received_at=datetime.now(UTC),
            correlation_id=new_correlation_id(),
        )
        if await deps.receive_incoming_message.execute(cmd):
            accepted += 1

    replies: list[dict[str, object]] = []
    conv = await deps.conversations.get_active_by_user_hash(user_hash)
    if body.sync and accepted > 0:
        await deps.process_conversation_turn.execute(user_hash, new_correlation_id())
        conv = await deps.conversations.get_active_by_user_hash(user_hash)
        if conv is not None:
            for out_msg in await deps.outbox.list_by_conversation(conv.id):
                if await deps.dispatch_outbox_message.execute(out_msg.id):
                    replies.append(
                        {
                            "outbox_id": out_msg.id,
                            "text": out_msg.text,
                            "ui_hint": out_msg.ui_hint,
                        }
                    )

    return {
        "accepted": accepted,
        "conversation_id": conv.id.value if conv else None,
        "conversation_status": conv.status.value if conv else None,
        "replies": replies,
    }


@router.get("/whatsapp/inbox/{phone}")
async def get_simulated_inbox(phone: str, request: Request) -> dict[str, object]:
    deps: HttpDependencies = request.app.state.deps
    if not deps.enable_simulator:
        raise HTTPException(status_code=404, detail="Simulador desabilitado.")
    phone_e164 = to_e164(phone)
    channel_msgs = deps.simulator_inbox_reader(phone_e164) if deps.simulator_inbox_reader else []
    user_hash = pseudonymize(phone_e164, deps.pseudonym_secret)
    conv = await deps.conversations.get_active_by_user_hash(user_hash)
    outbox_msgs = (
        [
            {"outbox_id": m.id, "text": m.text, "created_at": m.created_at.isoformat()}
            for m in await deps.outbox.list_by_conversation(conv.id)
        ]
        if conv is not None
        else []
    )
    return {
        "phone": phone_e164,
        "conversation_id": conv.id.value if conv else None,
        "conversation_status": conv.status.value if conv else None,
        "channel_messages": channel_msgs,
        "outbox_messages": outbox_msgs,
    }


@router.get("/helpdesk/tickets")
async def list_simulated_tickets(request: Request) -> dict[str, object]:
    deps: HttpDependencies = request.app.state.deps
    if not deps.enable_simulator:
        raise HTTPException(status_code=404, detail="Simulador desabilitado.")
    tickets = deps.simulator_tickets_reader() if deps.simulator_tickets_reader else []
    return {"tickets": tickets}


@router.post("/helpdesk/resolve/{conversation_id}")
async def simulate_helpdesk_resolve(
    conversation_id: str,
    request: Request,
    note: str = "Atendimento concluído no simulador.",
) -> dict[str, object]:
    deps: HttpDependencies = request.app.state.deps
    if not deps.enable_simulator:
        raise HTTPException(status_code=404, detail="Simulador desabilitado.")
    cmd = HelpdeskResolutionCommand(
        conversation_id=conversation_id,
        helpdesk_ticket_id=None,
        resolution_note=note,
        resolved_at=datetime.now(UTC),
        correlation_id=new_correlation_id(),
    )
    try:
        await deps.resume_after_handoff.execute(cmd)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "resumed", "conversation_id": conversation_id}
