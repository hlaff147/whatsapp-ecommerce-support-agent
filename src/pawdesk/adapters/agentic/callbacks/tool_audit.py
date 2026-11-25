"""Auditoria estruturada pós-execução de ferramenta (`after_tool_callback`)."""

from collections.abc import Callable
from typing import Any

import structlog
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from pawdesk.adapters.agentic.constants import FRAMEWORK_PASSTHROUGH_TOOLS, StateKey
from pawdesk.application.services.pii_redaction_service import PiiRedactionService

log = structlog.get_logger("pawdesk.agentic.tool_audit")


def make_after_tool_callback(
    redaction: PiiRedactionService,
) -> Callable[
    [BaseTool, dict[str, Any], ToolContext, dict[str, Any] | None], dict[str, Any] | None
]:
    """Registra execução das tools com argumentos mascarados e rastreia histórico no estado."""

    def after_tool_callback(
        tool: BaseTool,
        args: dict[str, Any],
        tool_context: ToolContext,
        tool_response: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        state = tool_context.state
        if tool.name not in FRAMEWORK_PASSTHROUGH_TOOLS:
            called = list(state.get(StateKey.TOOLS_CALLED_IN_TURN.value, []))
            called.append(tool.name)
            state[StateKey.TOOLS_CALLED_IN_TURN.value] = called

        safe_args = redaction.redact_args(dict(args))
        result_status = (
            str(tool_response.get("status", "unknown"))
            if isinstance(tool_response, dict)
            else "ok"
        )
        log.info(
            "adk_tool_executed",
            tool=tool.name,
            args_redacted=safe_args,
            result_status=result_status,
            conversation_id=state.get(StateKey.CONVERSATION_ID.value),
            correlation_id=state.get(StateKey.CORRELATION_ID.value),
        )
        return None

    return after_tool_callback
