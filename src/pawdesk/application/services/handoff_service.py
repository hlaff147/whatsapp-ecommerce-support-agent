"""Coordenação de handoff humano, pacote de contexto e retomada."""

from datetime import datetime

from pawdesk.application.dto.context import CallerContext
from pawdesk.application.dto.results import HandoffPackage, OutboundMessage
from pawdesk.application.messages import Messages
from pawdesk.application.ports.outbound.agent_runtime import CaseSummarizer
from pawdesk.application.ports.outbound.gateways import HelpdeskGateway
from pawdesk.application.ports.outbound.infra import Clock, UnitOfWork
from pawdesk.application.services.pii_redaction_service import PiiRedactionService
from pawdesk.domain.constants import (
    ConversationStatus,
    HandoffReason,
    HandoffStatus,
    MessageAuthor,
)
from pawdesk.domain.entities.conversation import Conversation, InboundMessage, MessageView
from pawdesk.domain.entities.handoff_ticket import HandoffTicket
from pawdesk.domain.services.handoff_policy import HandoffDecision
from pawdesk.shared.constants.regex import ORDER_NUMBER_RE
from pawdesk.shared.utils.ids import new_ulid


class HandoffService:
    """Cria resumo com PII mascarada, abre ticket no helpdesk e silencia o bot."""

    def __init__(
        self,
        *,
        summarizer: CaseSummarizer,
        helpdesk: HelpdeskGateway,
        redaction: PiiRedactionService,
        clock: Clock,
        messages: Messages,
    ) -> None:
        self._summarizer = summarizer
        self._helpdesk = helpdesk
        self._redaction = redaction
        self._clock = clock
        self._messages = messages

    async def start(
        self,
        *,
        uow: UnitOfWork,
        conv: Conversation,
        caller: CallerContext,
        decision: HandoffDecision,
        tools_called: tuple[str, ...] = (),
        now: datetime | None = None,
    ) -> HandoffTicket:
        effective_now = now or self._clock.now()
        reason = decision.reason or HandoffReason.OUT_OF_SCOPE
        recent = await uow.conversations.list_recent_messages(conv.id, limit=20)
        order_numbers = self._extract_order_numbers(recent)

        summary = await self._summarizer.summarize(
            recent,
            reason=reason.value,
            order_numbers=order_numbers,
            max_lines=5,
        )
        summary_redacted = self._redaction.redact_text(summary)

        sentiment = (
            "frustrado/urgente"
            if decision.urgent
            else ("insatisfeito" if reason == HandoffReason.DELIVERY_DELAY else "neutro")
        )
        package = HandoffPackage(
            conversation_id=conv.id.value,
            summary=summary_redacted,
            customer_first_name=caller.customer_first_name,
            verification_level=caller.level,
            order_numbers=order_numbers,
            actions_executed=tools_called,
            reason=reason,
            priority=decision.priority,
            urgent=decision.urgent,
            sentiment=sentiment,
            suggested_next_steps=self._suggest_next_steps(reason),
        )
        created = await self._helpdesk.create_ticket(package)

        ticket = HandoffTicket(
            id=new_ulid(),
            conversation_id=conv.id,
            reason=reason,
            priority=decision.priority,
            urgent=decision.urgent,
            summary=summary_redacted,
            helpdesk_ticket_id=created.external_ticket_id,
            status=HandoffStatus.OPEN,
            created_at=effective_now,
        )
        await uow.handoffs.create(ticket)
        await uow.conversations.update_status(conv.id, ConversationStatus.WITH_HUMAN)
        await uow.audit_logs.record(
            conversation_id=conv.id.value,
            actor=MessageAuthor.SYSTEM.value,
            action="HANDOFF_STARTED",
            tool=None,
            args_redacted={
                "reason": reason.value,
                "priority": decision.priority.value,
                "ticket_id": ticket.id,
            },
            result_status="OPEN",
            correlation_id=caller.correlation_id,
            created_at=effective_now,
        )
        return ticket

    async def forward_to_human(
        self,
        *,
        uow: UnitOfWork,
        conv: Conversation,
        pending: list[InboundMessage],
    ) -> None:
        ticket = await uow.handoffs.get_open_by_conversation(conv.id)
        external_id = ticket.helpdesk_ticket_id if ticket else None
        for msg in pending:
            redacted = self._redaction.redact_text(msg.text)
            await self._helpdesk.forward_message(
                conversation_id=conv.id.value,
                external_ticket_id=external_id,
                text_redacted=redacted,
            )

    async def resume(
        self,
        *,
        uow: UnitOfWork,
        conv: Conversation,
        correlation_id: str,
        resolution_note: str | None = None,
    ) -> OutboundMessage | None:
        now = self._clock.now()
        ticket = await uow.handoffs.get_open_by_conversation(conv.id)
        if ticket is not None:
            await uow.handoffs.update_status(
                ticket.id,
                HandoffStatus.RESOLVED,
                resolved_at=now,
            )
        await uow.conversations.update_status(conv.id, ConversationStatus.ACTIVE)
        await uow.conversations.append_system_message(
            conv,
            author=MessageAuthor.SYSTEM,
            content_redacted=self._redaction.redact_text(
                f"Handoff encerrado pelo atendente. {resolution_note or ''}".strip()
            ),
            created_at=now,
        )
        await uow.audit_logs.record(
            conversation_id=conv.id.value,
            actor=MessageAuthor.HUMAN.value,
            action="HANDOFF_RESOLVED",
            tool=None,
            args_redacted={"ticket_id": ticket.id if ticket else None},
            result_status="RESOLVED",
            correlation_id=correlation_id,
            created_at=now,
        )
        outbound = OutboundMessage(
            id=new_ulid(),
            conversation_id=conv.id.value,
            recipient_phone=conv.channel_user_phone,
            text=self._messages.handoff_resumed,
            ui_hint=None,
            created_at=now,
        )
        await uow.outbox.add(outbound)
        return outbound

    def _extract_order_numbers(self, messages: list[MessageView]) -> tuple[str, ...]:
        seen: list[str] = []
        for msg in messages:
            for match in ORDER_NUMBER_RE.finditer(msg.content_redacted):
                order_num = f"PD-{match.group(1)}"
                if order_num not in seen:
                    seen.append(order_num)
        return tuple(seen)

    def _suggest_next_steps(self, reason: HandoffReason) -> str:
        mapping = {
            HandoffReason.DELIVERY_DELAY: (
                "Verificar ocorrência na transportadora e alinhar novo prazo com o cliente."
            ),
            HandoffReason.PET_HEALTH_EMERGENCY: (
                "Priorizar encaminhamento ao canal veterinário e confirmar atendimento."
            ),
            HandoffReason.FRUSTRATION: (
                "Acolher a reclamação com empatia e resolver a pendência prioritariamente."
            ),
            HandoffReason.LEGAL_RISK: (
                "Tratar com prioridade urgente conforme protocolo de ouvidoria."
            ),
            HandoffReason.VERIFICATION_FAILED: (
                "Confirmar titularidade manualmente antes de fornecer dados sensíveis."
            ),
        }
        return mapping.get(
            reason, "Assumir o atendimento a partir do resumo acima sem repetir perguntas."
        )
