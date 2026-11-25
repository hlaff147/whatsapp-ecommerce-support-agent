"""Leitura segura do CallerContext a partir do estado da sessão ADK (ADR-05)."""

from typing import Any, Protocol

from pawdesk.adapters.agentic.constants import StateKey
from pawdesk.application.dto.context import CallerContext
from pawdesk.domain.constants import VerificationLevel
from pawdesk.domain.value_objects.ids import CustomerId


class _StateReadable(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...


def caller_from_state(state: _StateReadable) -> CallerContext:
    """Constrói CallerContext exclusivamente a partir do estado confiável da sessão."""
    raw_cid = state.get(StateKey.CUSTOMER_ID.value)
    raw_first_name = state.get(StateKey.CUSTOMER_FIRST_NAME.value)
    return CallerContext(
        customer_id=CustomerId(str(raw_cid)) if raw_cid else None,
        customer_first_name=str(raw_first_name) if raw_first_name else None,
        level=VerificationLevel(int(state.get(StateKey.VERIFICATION_LEVEL.value, 0))),
        conversation_id=str(state.get(StateKey.CONVERSATION_ID.value, "")),
        correlation_id=str(state.get(StateKey.CORRELATION_ID.value, "")),
    )
