"""Caso de uso: listar pedidos recentes do cliente autenticado (UC-01)."""

from pawdesk.application.dto.context import CallerContext
from pawdesk.application.dto.results import OrderSummaryView
from pawdesk.application.ports.outbound.repositories import OrderRepository
from pawdesk.domain.constants import VerificationLevel
from pawdesk.shared.constants.limits import LIST_ORDERS_MAX


class ListCustomerOrders:
    """Lista os últimos pedidos apenas do cliente identificado na sessão."""

    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    async def execute(
        self, caller: CallerContext, limit: int = LIST_ORDERS_MAX
    ) -> list[OrderSummaryView]:
        caller.require(VerificationLevel.PHONE_MATCH)
        assert caller.customer_id is not None
        bounded_limit = max(1, min(limit, LIST_ORDERS_MAX))
        orders = await self._orders.list_recent_by_customer(caller.customer_id, bounded_limit)
        return [OrderSummaryView.from_order(order) for order in orders]
