"""Coletor de telemetria (logs estruturados, OpenTelemetry spans e métricas)."""

from collections import Counter
from decimal import Decimal
from threading import Lock

import structlog

from pawdesk.adapters.outbound.observability.otel import get_tracer
from pawdesk.application.dto.agent_io import AgentTurnResult
from pawdesk.domain.entities.conversation import Conversation
from pawdesk.domain.services.handoff_policy import HandoffDecision

log = structlog.get_logger("pawdesk.telemetry")


class InMemoryTelemetry:
    """Implementa Telemetry agregando métricas operacionais e emitindo logs/spans."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._turns = 0
        self._handoffs = 0
        self._total_cost_usd = Decimal("0")
        self._latencies_ms: list[int] = []
        self._handoff_reasons: Counter[str] = Counter()
        self._tool_calls: Counter[str] = Counter()
        self._guardrail_triggers: Counter[str] = Counter()
        self._outbox_events: Counter[str] = Counter()
        self._tokens_in = 0
        self._tokens_out = 0
        self._tracer = get_tracer("pawdesk.turn")

    async def record_turn(
        self,
        *,
        conversation: Conversation,
        result: AgentTurnResult,
        handoff_decision: HandoffDecision,
        cost_usd: Decimal,
        latency_ms: int,
    ) -> None:
        with self._tracer.start_as_current_span("conversation_turn") as span:
            span.set_attribute("conversation.id", conversation.id.value)
            span.set_attribute("verification.level", int(conversation.verification_level))
            span.set_attribute("agent.name", result.agent_name or "unknown")
            span.set_attribute("handoff.triggered", handoff_decision.handoff)
            if handoff_decision.reason:
                span.set_attribute("handoff.reason", handoff_decision.reason.value)

        with self._lock:
            self._turns += 1
            self._total_cost_usd += cost_usd
            self._latencies_ms.append(latency_ms)
            if len(self._latencies_ms) > 1000:
                self._latencies_ms = self._latencies_ms[-1000:]
            for tool_name in result.tools_called:
                self._tool_calls[tool_name] += 1
            for usage in result.usage:
                self._tokens_in += usage.input_tokens
                self._tokens_out += usage.output_tokens
            if handoff_decision.handoff:
                self._handoffs += 1
                reason_key = handoff_decision.reason.value if handoff_decision.reason else "UNKNOWN"
                self._handoff_reasons[reason_key] += 1

        log.info(
            "turn_completed",
            conversation_id=conversation.id.value,
            user_hash=conversation.channel_user_hash,
            agent_name=result.agent_name,
            tools_called=list(result.tools_called),
            handoff=handoff_decision.handoff,
            handoff_reason=handoff_decision.reason.value if handoff_decision.reason else None,
            cost_usd=str(cost_usd),
            latency_ms=latency_ms,
            trace_id=result.trace_id,
        )

    def increment_guardrail_trigger(self, trigger_type: str) -> None:
        with self._lock:
            self._guardrail_triggers[trigger_type] += 1
        log.warning("guardrail_triggered", trigger_type=trigger_type)

    def increment_outbox_event(self, status: str) -> None:
        with self._lock:
            self._outbox_events[status] += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            turns = self._turns
            handoffs = self._handoffs
            containment = round((turns - handoffs) / turns, 4) if turns > 0 else 1.0
            sorted_lat = sorted(self._latencies_ms)
            p95_idx = int(0.95 * (len(sorted_lat) - 1)) if sorted_lat else 0
            p95 = sorted_lat[p95_idx] if sorted_lat else 0
            return {
                "turns_total": turns,
                "handoffs_total": handoffs,
                "containment_rate": containment,
                "latency_p95_ms": p95,
                "total_cost_usd": str(self._total_cost_usd),
                "tokens_in_total": self._tokens_in,
                "tokens_out_total": self._tokens_out,
                "handoff_reasons": dict(self._handoff_reasons),
                "tool_calls": dict(self._tool_calls),
                "guardrail_triggers": dict(self._guardrail_triggers),
                "outbox_events": dict(self._outbox_events),
            }
