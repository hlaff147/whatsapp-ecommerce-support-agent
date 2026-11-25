"""Contratos de entrada e saída entre o núcleo e o runtime agêntico."""

from dataclasses import dataclass

from pawdesk.application.dto.context import CallerContext


@dataclass(frozen=True)
class AgentTurnRequest:
    session_id: str
    user_id: str
    text: str
    caller: CallerContext
    confirmed_action_id: str | None = None
    fallback_count: int = 0
    tool_error_count: int = 0
    verification_attempts: int = 0
    locale: str = "pt-BR"


@dataclass(frozen=True)
class HandoffSignal:
    reason: str
    note: str = ""


@dataclass(frozen=True)
class UiHint:
    kind: str  # "confirm_buttons" | "list" | "url_button"
    payload: dict[str, object]


@dataclass(frozen=True)
class TokenUsage:
    model: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class AgentTurnResult:
    reply_text: str
    agent_name: str | None = None
    handoff: HandoffSignal | None = None
    ui_hint: UiHint | None = None
    tools_called: tuple[str, ...] = ()
    usage: tuple[TokenUsage, ...] = ()
    trace_id: str | None = None
    fallback_count: int = 0
    tool_error_count: int = 0
    late_order_requires_handoff: bool = False
