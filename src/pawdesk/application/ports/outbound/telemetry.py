"""Contratos de telemetria e cálculo de custo."""

from decimal import Decimal
from typing import Protocol

from pawdesk.application.dto.agent_io import AgentTurnResult, TokenUsage
from pawdesk.domain.entities.conversation import Conversation
from pawdesk.domain.services.handoff_policy import HandoffDecision


class CostCalculator(Protocol):
    def calculate_usd(self, usage: tuple[TokenUsage, ...]) -> Decimal: ...


class Telemetry(Protocol):
    async def record_turn(
        self,
        *,
        conversation: Conversation,
        result: AgentTurnResult,
        handoff_decision: HandoffDecision,
        cost_usd: Decimal,
        latency_ms: int,
    ) -> None: ...

    def increment_guardrail_trigger(self, trigger_type: str) -> None: ...
    def increment_outbox_event(self, status: str) -> None: ...
    def snapshot(self) -> dict[str, object]: ...
