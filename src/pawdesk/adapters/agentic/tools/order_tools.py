"""Tools de pedidos e entregas (adaptadores de entrada finos -> Use Cases)."""

from collections.abc import Callable

from google.adk.tools.tool_context import ToolContext

from pawdesk.adapters.agentic.constants import StateKey
from pawdesk.adapters.agentic.tools._context import caller_from_state
from pawdesk.adapters.agentic.tools._guard import guarded_tool
from pawdesk.adapters.agentic.tools._result import ToolResult
from pawdesk.application.use_cases.estimate_delivery_by_zip import EstimateDeliveryByZip
from pawdesk.application.use_cases.get_order_status import GetOrderStatus
from pawdesk.application.use_cases.list_customer_orders import ListCustomerOrders
from pawdesk.application.use_cases.track_shipment import TrackShipment
from pawdesk.domain.value_objects.address import ZipCode
from pawdesk.domain.value_objects.ids import OrderNumber, Sku
from pawdesk.shared.constants.limits import LIST_ORDERS_MAX


def build_order_tools(
    *,
    list_orders_uc: ListCustomerOrders,
    get_order_status_uc: GetOrderStatus,
    track_shipment_uc: TrackShipment,
    estimate_delivery_uc: EstimateDeliveryByZip,
) -> dict[str, Callable[..., object]]:
    """Constrói as tools de pedido e entrega ligadas aos respectivos casos de uso."""

    @guarded_tool
    async def get_my_orders(
        limit: int = LIST_ORDERS_MAX, tool_context: ToolContext | None = None
    ) -> dict[str, object]:
        """Lista os pedidos recentes do cliente autenticado na conversa atual.

        Use quando o cliente perguntar sobre seus pedidos sem informar um número específico.

        Args:
            limit: Quantidade máxima de pedidos recentes a retornar (padrão 5, máximo 5).

        Returns:
            dict com status "success" e lista resumida de pedidos, ou "error".
        """
        assert tool_context is not None
        caller = caller_from_state(tool_context.state)
        views = await list_orders_uc.execute(caller, limit=limit)
        if len(views) == 1:
            tool_context.state[StateKey.ACTIVE_ORDER_NUMBER.value] = views[0].order_number
        return ToolResult.ok(orders=[v.to_llm_view() for v in views])

    @guarded_tool
    async def get_order_status(
        order_number: str, tool_context: ToolContext | None = None
    ) -> dict[str, object]:
        """Consulta status detalhado, itens e situação de prazo de um pedido do cliente atual.

        Use quando o cliente informar ou perguntar por um número de pedido específico.

        Args:
            order_number: Número do pedido informado pelo cliente (ex.: "PD-104822").

        Returns:
            dict com status "success" e dados (is_late, requires_handoff), ou "error".
        """
        assert tool_context is not None
        caller = caller_from_state(tool_context.state)
        view = await get_order_status_uc.execute(caller, OrderNumber.parse(order_number))
        tool_context.state[StateKey.ACTIVE_ORDER_NUMBER.value] = view.order_number
        if view.delay.requires_handoff:
            tool_context.state[StateKey.LATE_ORDER_HANDOFF.value] = True
        return ToolResult.ok(order=view.to_llm_view())

    @guarded_tool
    async def track_shipment(
        order_number: str, tool_context: ToolContext | None = None
    ) -> dict[str, object]:
        """Rastreia a entrega de um pedido: transportadora, link, última movimentação e previsão.

        Use quando o cliente pedir link de rastreio, onde está a entrega ou últimas movimentações.

        Args:
            order_number: Número do pedido (ex.: "PD-104822").

        Returns:
            dict com status "success" e eventos de rastreamento, ou "error".
        """
        assert tool_context is not None
        caller = caller_from_state(tool_context.state)
        view = await track_shipment_uc.execute(caller, OrderNumber.parse(order_number))
        tool_context.state[StateKey.ACTIVE_ORDER_NUMBER.value] = view.order_number
        if view.delay.requires_handoff:
            tool_context.state[StateKey.LATE_ORDER_HANDOFF.value] = True
        return ToolResult.ok(shipment=view.to_llm_view())

    @guarded_tool
    async def estimate_delivery_by_zip(
        zip_code: str, sku: str, tool_context: ToolContext | None = None
    ) -> dict[str, object]:
        """Estima prazo de entrega e frete para um CEP e produto (SKU) antes da compra.

        Nunca invente prazos; consulte sempre esta ferramenta.

        Args:
            zip_code: CEP de entrega com 8 dígitos (ex.: "01310-100").
            sku: Código SKU do produto no catálogo (ex.: "RAC-GAT-10KG").

        Returns:
            dict com prazo em dias úteis, data estimada, valor do frete e transportadora.
        """
        _ = tool_context
        view = await estimate_delivery_uc.execute(ZipCode.parse(zip_code), Sku(sku))
        return ToolResult.ok(estimate=view.to_llm_view())

    return {
        "get_my_orders": get_my_orders,
        "get_order_status": get_order_status,
        "track_shipment": track_shipment,
        "estimate_delivery_by_zip": estimate_delivery_by_zip,
    }
