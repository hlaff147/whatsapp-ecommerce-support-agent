"""Tool de verificação reforçada de identidade (RN-01 Nível 2)."""

from collections.abc import Callable

from google.adk.tools.tool_context import ToolContext

from pawdesk.adapters.agentic.constants import StateKey
from pawdesk.adapters.agentic.tools._context import caller_from_state
from pawdesk.adapters.agentic.tools._guard import guarded_tool
from pawdesk.adapters.agentic.tools._result import ToolResult
from pawdesk.application.use_cases.verify_customer_identity import VerifyCustomerIdentity
from pawdesk.domain.value_objects.ids import OrderNumber


def build_identity_tools(
    *, verify_identity_uc: VerifyCustomerIdentity
) -> dict[str, Callable[..., object]]:
    """Constrói a tool de verificação reforçada (step-up)."""

    @guarded_tool
    async def verify_customer_identity(
        order_number: str,
        cpf_last3: str,
        tool_context: ToolContext | None = None,
    ) -> dict[str, object]:
        """Eleva a verificação de identidade usando nº do pedido + 3 últimos dígitos do CPF.

        Nunca peça o CPF completo. Use apenas os 3 últimos dígitos informados pelo cliente.

        Args:
            order_number: Número de um pedido do cliente (ex.: "PD-104822").
            cpf_last3: Os 3 últimos dígitos do CPF do titular (ex.: "456").

        Returns:
            dict indicando se a verificação foi aprovada, tentativas restantes ou bloqueio/handoff.
        """
        assert tool_context is not None
        caller = caller_from_state(tool_context.state)
        view = await verify_identity_uc.execute(
            caller=caller,
            order_number=OrderNumber.parse(order_number),
            cpf_last3=cpf_last3,
        )
        tool_context.state[StateKey.VERIFICATION_LEVEL.value] = int(view.verification_level)
        if view.verified:
            tool_context.state[StateKey.ACTIVE_ORDER_NUMBER.value] = OrderNumber.parse(
                order_number
            ).value
            tool_context.state[StateKey.VERIFICATION_ATTEMPTS.value] = 0
        if view.should_handoff:
            tool_context.state[StateKey.HANDOFF_REQUESTED.value] = {
                "reason": "VERIFICATION_FAILED",
                "note": view.message,
            }
        return ToolResult.ok(**view.to_llm_view())

    return {"verify_customer_identity": verify_customer_identity}
