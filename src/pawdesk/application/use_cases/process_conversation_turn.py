"""Caso de uso central: orquestra a execução de um turno de conversa."""

from collections.abc import Callable
from datetime import datetime
from time import monotonic

from pawdesk.application.dto.agent_io import (
    AgentTurnRequest,
    AgentTurnResult,
    HandoffSignal,
)
from pawdesk.application.dto.results import OutboundMessage
from pawdesk.application.errors import AgentRuntimeError
from pawdesk.application.messages import Messages
from pawdesk.application.ports.outbound.agent_runtime import AgentRuntime
from pawdesk.application.ports.outbound.infra import (
    Clock,
    ConversationLock,
    TurnScheduler,
    UnitOfWork,
)
from pawdesk.application.ports.outbound.repositories import ConversationRepository
from pawdesk.application.ports.outbound.telemetry import CostCalculator, Telemetry
from pawdesk.application.services.handoff_service import HandoffService
from pawdesk.application.services.identity_service import IdentityService
from pawdesk.domain.constants import ConversationStatus, HandoffReason
from pawdesk.domain.entities.conversation import InboundMessage
from pawdesk.domain.services.handoff_policy import (
    HandoffDecision,
    HandoffPolicy,
    HandoffSignals,
)
from pawdesk.shared.constants.limits import CONVERSATION_LOCK_TTL_S
from pawdesk.shared.utils.dates import is_business_hours
from pawdesk.shared.utils.ids import new_ulid
from pawdesk.shared.utils.text import truncate_for_whatsapp


class ProcessConversationTurn:
    """Executa um turno sob lock por conversa com commit transacional de resposta + outbox."""

    def __init__(
        self,
        *,
        lock: ConversationLock,
        conversations: ConversationRepository,
        uow_factory: Callable[[], UnitOfWork],
        identity: IdentityService,
        agent: AgentRuntime,
        handoff: HandoffService,
        scheduler: TurnScheduler,
        telemetry: Telemetry,
        cost_calculator: CostCalculator,
        handoff_policy: HandoffPolicy,
        clock: Clock,
        messages: Messages,
        vet_channel_available: bool = True,
    ) -> None:
        self._lock = lock
        self._conversations = conversations
        self._uow_factory = uow_factory
        self._identity = identity
        self._agent = agent
        self._handoff = handoff
        self._scheduler = scheduler
        self._telemetry = telemetry
        self._cost = cost_calculator
        self._handoff_policy = handoff_policy
        self._clock = clock
        self._messages = messages
        self._vet_channel_available = vet_channel_available

    async def execute(self, channel_user_hash: str, correlation_id: str) -> None:
        started = monotonic()
        outbound_id: str | None = None
        conv_for_telemetry = None
        result_for_telemetry: AgentTurnResult | None = None
        decision_for_telemetry: HandoffDecision | None = None
        cost_usd = self._cost.calculate_usd(())

        async with self._lock.hold(f"conv:{channel_user_hash}", CONVERSATION_LOCK_TTL_S):
            conv = await self._conversations.get_active_by_user_hash(channel_user_hash)
            if conv is None:
                return

            pending = await self._conversations.list_pending_inbound(conv.id)
            if not pending:
                return

            now = self._clock.now()
            if conv.status is ConversationStatus.WITH_HUMAN:
                async with self._uow_factory() as uow:
                    await self._handoff.forward_to_human(uow=uow, conv=conv, pending=pending)
                    await uow.conversations.mark_processed(pending, now)
                return

            caller = await self._identity.resolve_caller(conv, correlation_id)
            combined_text = "\n".join(m.text for m in pending if m.text.strip())
            confirmed_action_id = self._extract_confirmed_action_id(pending)

            request = AgentTurnRequest(
                session_id=conv.adk_session_id,
                user_id=conv.channel_user_hash,
                text=combined_text,
                caller=caller,
                confirmed_action_id=confirmed_action_id,
            )

            try:
                result = await self._agent.run_turn(request)
            except AgentRuntimeError:
                result = AgentTurnResult(
                    reply_text=self._messages.agent_error,
                    handoff=HandoffSignal(reason=HandoffReason.AGENT_ERROR.value),
                )

            agent_reason = self._parse_reason(result.handoff.reason) if result.handoff else None
            refreshed_conv = await self._conversations.get_by_id(conv.id) or conv
            decision = self._handoff_policy.decide(
                HandoffSignals(
                    user_asked_human=(agent_reason == HandoffReason.USER_REQUESTED),
                    fallback_count=result.fallback_count,
                    tool_error_count=result.tool_error_count,
                    verification_attempts=refreshed_conv.verification_attempts,
                    last_user_text=combined_text,
                    agent_requested=agent_reason,
                    late_order_requires_handoff=result.late_order_requires_handoff,
                )
            )

            final_text = self._compose_reply(result=result, decision=decision, now=now)
            final_result = AgentTurnResult(
                reply_text=final_text,
                agent_name=result.agent_name,
                handoff=result.handoff,
                ui_hint=result.ui_hint,
                tools_called=result.tools_called,
                usage=result.usage,
                trace_id=result.trace_id or correlation_id,
                fallback_count=result.fallback_count,
                tool_error_count=result.tool_error_count,
                late_order_requires_handoff=result.late_order_requires_handoff,
            )

            cost_usd = self._cost.calculate_usd(final_result.usage)
            latency_ms = max(1, int((monotonic() - started) * 1000))
            outbound = OutboundMessage(
                id=new_ulid(),
                conversation_id=conv.id.value,
                recipient_phone=conv.channel_user_phone,
                text=final_text,
                ui_hint=(
                    {"kind": final_result.ui_hint.kind, **final_result.ui_hint.payload}
                    if final_result.ui_hint is not None
                    else None
                ),
                created_at=now,
            )

            async with self._uow_factory() as uow:
                await uow.conversations.append_agent_message(
                    conv,
                    final_result,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    created_at=now,
                )
                await uow.conversations.mark_processed(pending, now)
                await uow.outbox.add(outbound)
                if decision.handoff:
                    await self._handoff.start(
                        uow=uow,
                        conv=refreshed_conv,
                        caller=caller,
                        decision=decision,
                        tools_called=final_result.tools_called,
                        now=now,
                    )

            outbound_id = outbound.id
            conv_for_telemetry = refreshed_conv
            result_for_telemetry = final_result
            decision_for_telemetry = decision

        if outbound_id is not None:
            await self._scheduler.schedule_outbox_dispatch(outbound_id)

        if (
            conv_for_telemetry is not None
            and result_for_telemetry is not None
            and decision_for_telemetry is not None
        ):
            latency_ms = max(1, int((monotonic() - started) * 1000))
            await self._telemetry.record_turn(
                conversation=conv_for_telemetry,
                result=result_for_telemetry,
                handoff_decision=decision_for_telemetry,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
            )

    def _extract_confirmed_action_id(self, pending: list[InboundMessage]) -> str | None:
        for msg in reversed(pending):
            payload = msg.interactive_payload
            if payload and payload.startswith("confirm:"):
                return payload.removeprefix("confirm:")
        return None

    def _parse_reason(self, raw: str) -> HandoffReason:
        try:
            return HandoffReason(raw)
        except ValueError:
            return HandoffReason.OUT_OF_SCOPE

    def _compose_reply(
        self, *, result: AgentTurnResult, decision: HandoffDecision, now: datetime
    ) -> str:
        text = result.reply_text.strip()
        if not decision.handoff:
            return truncate_for_whatsapp(text)

        if decision.reason == HandoffReason.PET_HEALTH_EMERGENCY:
            emergency_msg = (
                self._messages.pet_emergency_with_vet_channel
                if self._vet_channel_available
                else self._messages.pet_emergency_base
            )
            if not is_business_hours(now):
                return truncate_for_whatsapp(
                    f"{emergency_msg}\n\n{self._messages.handoff_out_of_hours}"
                )
            return truncate_for_whatsapp(emergency_msg)

        hours_notice = (
            self._messages.handoff_in_business_hours
            if is_business_hours(now)
            else self._messages.handoff_out_of_hours
        )
        if decision.reason == HandoffReason.FRUSTRATION:
            base = self._messages.handoff_urgent_notice
            return truncate_for_whatsapp(f"{base}\n\n{hours_notice}")

        if "horário comercial" in text.lower() or "em poucos minutos" in text.lower():
            return truncate_for_whatsapp(text)

        if text:
            return truncate_for_whatsapp(f"{text}\n\n{hours_notice}")
        return truncate_for_whatsapp(hours_notice)
