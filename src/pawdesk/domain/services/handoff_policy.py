"""Política objetiva de decisão de handoff humano (seção 9 do negócio)."""

from dataclasses import dataclass

from pawdesk.domain.constants import (
    FRUSTRATION_TERMS,
    HUMAN_REQUEST_TERMS,
    LEGAL_RISK_TERMS,
    HandoffPriority,
    HandoffReason,
)
from pawdesk.shared.constants.limits import (
    MAX_FALLBACKS_BEFORE_HANDOFF,
    MAX_TOOL_ERRORS_BEFORE_HANDOFF,
    MAX_VERIFICATION_ATTEMPTS,
)


@dataclass(frozen=True)
class HandoffSignals:
    user_asked_human: bool
    fallback_count: int
    tool_error_count: int
    verification_attempts: int
    last_user_text: str
    agent_requested: HandoffReason | None = None
    late_order_requires_handoff: bool = False


@dataclass(frozen=True)
class HandoffDecision:
    handoff: bool
    reason: HandoffReason | None = None
    priority: HandoffPriority = HandoffPriority.NORMAL
    urgent: bool = False


class HandoffPolicy:
    """Combina sinais objetivos do turno para decidir o handoff de forma determinística."""

    def __init__(
        self,
        max_fallbacks: int = MAX_FALLBACKS_BEFORE_HANDOFF,
        max_tool_errors: int = MAX_TOOL_ERRORS_BEFORE_HANDOFF,
        max_verif_attempts: int = MAX_VERIFICATION_ATTEMPTS,
    ) -> None:
        self._max_fallbacks = max_fallbacks
        self._max_tool_errors = max_tool_errors
        self._max_verif_attempts = max_verif_attempts

    def decide(self, signals: HandoffSignals) -> HandoffDecision:
        raw_text = signals.last_user_text.strip()
        lower_text = raw_text.lower()

        if any(term in lower_text for term in LEGAL_RISK_TERMS):
            return HandoffDecision(
                handoff=True,
                reason=HandoffReason.LEGAL_RISK,
                priority=HandoffPriority.URGENT,
                urgent=True,
            )

        if signals.agent_requested in {
            HandoffReason.PET_HEALTH_EMERGENCY,
            HandoffReason.FRAUD_SUSPECTED,
            HandoffReason.LEGAL_RISK,
        }:
            return HandoffDecision(
                handoff=True,
                reason=signals.agent_requested,
                priority=HandoffPriority.URGENT,
                urgent=True,
            )

        if signals.user_asked_human or any(term in lower_text for term in HUMAN_REQUEST_TERMS):
            return HandoffDecision(
                handoff=True,
                reason=HandoffReason.USER_REQUESTED,
                priority=HandoffPriority.HIGH,
                urgent=False,
            )

        letters = [ch for ch in raw_text if ch.isalpha()]
        is_shouting = len(letters) > 20 and raw_text == raw_text.upper()
        if is_shouting or any(term in lower_text for term in FRUSTRATION_TERMS):
            return HandoffDecision(
                handoff=True,
                reason=HandoffReason.FRUSTRATION,
                priority=HandoffPriority.URGENT,
                urgent=True,
            )

        if signals.verification_attempts >= self._max_verif_attempts:
            return HandoffDecision(
                handoff=True,
                reason=HandoffReason.VERIFICATION_FAILED,
                priority=HandoffPriority.MEDIUM,
                urgent=False,
            )

        if signals.late_order_requires_handoff:
            return HandoffDecision(
                handoff=True,
                reason=HandoffReason.DELIVERY_DELAY,
                priority=HandoffPriority.HIGH,
                urgent=False,
            )

        if signals.fallback_count >= self._max_fallbacks:
            return HandoffDecision(
                handoff=True,
                reason=HandoffReason.REPEATED_FAILURE,
                priority=HandoffPriority.HIGH,
                urgent=False,
            )

        if signals.tool_error_count >= self._max_tool_errors:
            return HandoffDecision(
                handoff=True,
                reason=HandoffReason.TOOL_UNAVAILABLE,
                priority=HandoffPriority.HIGH,
                urgent=False,
            )

        if signals.agent_requested is not None:
            priority = (
                HandoffPriority.HIGH
                if signals.agent_requested
                in {
                    HandoffReason.AGENT_ERROR,
                    HandoffReason.TOOL_UNAVAILABLE,
                    HandoffReason.USER_REQUESTED,
                }
                else HandoffPriority.NORMAL
            )
            return HandoffDecision(
                handoff=True,
                reason=signals.agent_requested,
                priority=priority,
                urgent=False,
            )

        return HandoffDecision(handoff=False)
