"""Tool de controle para sinalização de handoff humano (ADR-06)."""

from collections.abc import Callable

from google.adk.tools.tool_context import ToolContext

from pawdesk.adapters.agentic.constants import StateKey
from pawdesk.adapters.agentic.tools._guard import guarded_tool
from pawdesk.adapters.agentic.tools._result import ToolResult
from pawdesk.domain.constants import HandoffReason


def build_control_tools() -> dict[str, Callable[..., object]]:
    """Constrói tools de controle de fluxo da conversa."""

    @guarded_tool
    async def request_human_handoff(
        reason_code: str,
        note: str = "",
        tool_context: ToolContext | None = None,
    ) -> dict[str, object]:
        """Sinaliza que a conversa deve ser transferida para um atendente humano.

        Use quando o cliente pedir atendente/humano, demonstrar frustração, houver atraso
        acima de 3 dias úteis, falha de verificação, risco legal/fraude, emergência de saúde pet
        ou assunto fora de escopo.

        Args:
            reason_code: Código do motivo (USER_REQUESTED, FRUSTRATION, DELIVERY_DELAY,
                VERIFICATION_FAILED, LEGAL_RISK, FRAUD_SUSPECTED, PET_HEALTH_EMERGENCY,
                OUT_OF_SCOPE).
            note: Breve contexto do motivo da transferência.

        Returns:
            dict confirmando o registro do sinal de handoff para a aplicação.
        """
        assert tool_context is not None
        try:
            normalized_reason = HandoffReason(reason_code.strip().upper()).value
        except ValueError:
            normalized_reason = HandoffReason.OUT_OF_SCOPE.value

        tool_context.state[StateKey.HANDOFF_REQUESTED.value] = {
            "reason": normalized_reason,
            "note": note[:200],
        }
        return ToolResult.ok(handoff_signaled=True, reason=normalized_reason)

    return {"request_human_handoff": request_human_handoff}
