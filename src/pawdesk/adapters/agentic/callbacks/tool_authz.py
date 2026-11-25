"""Autorização determinística e orçamento de ferramentas (`before_tool_callback`)."""

from collections.abc import Callable
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from pawdesk.adapters.agentic.constants import FRAMEWORK_PASSTHROUGH_TOOLS, StateKey
from pawdesk.adapters.agentic.tools._result import ToolResult
from pawdesk.adapters.agentic.tools.registry import ToolRegistry
from pawdesk.application.constants import ErrorCode
from pawdesk.domain.constants import HandoffReason, VerificationLevel
from pawdesk.shared.constants.limits import MAX_TOOL_CALLS_PER_TURN


def make_before_tool_callback(
    registry: ToolRegistry,
) -> Callable[[BaseTool, dict[str, Any], ToolContext], dict[str, Any] | None]:
    """Valida orçamento por turno e nível mínimo de verificação antes de executar tools."""

    def before_tool_callback(
        tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
    ) -> dict[str, Any] | None:
        _ = args
        state = tool_context.state

        calls = int(state.get(StateKey.TOOL_CALLS_IN_TURN.value, 0)) + 1
        state[StateKey.TOOL_CALLS_IN_TURN.value] = calls
        if calls > MAX_TOOL_CALLS_PER_TURN:
            state[StateKey.HANDOFF_REQUESTED.value] = {
                "reason": HandoffReason.REPEATED_FAILURE.value,
                "note": "orçamento de tools por turno excedido",
            }
            return ToolResult.fail(
                ErrorCode.TOOL_BUDGET_EXCEEDED,
                "Vou transferir você para um atendente humano continuar te ajudando.",
            )

        if tool.name in FRAMEWORK_PASSTHROUGH_TOOLS:
            return None

        spec = registry.find(tool.name)
        if spec is None:
            return ToolResult.fail(ErrorCode.NOT_FOUND, "Ferramenta não autorizada.")

        level = VerificationLevel(int(state.get(StateKey.VERIFICATION_LEVEL.value, 0)))
        if level < spec.min_level:
            return ToolResult.fail(
                ErrorCode.VERIFICATION_REQUIRED,
                "É preciso verificar a identidade do cliente antes dessa consulta.",
                required_level=spec.min_level.name,
            )

        return None

    return before_tool_callback
