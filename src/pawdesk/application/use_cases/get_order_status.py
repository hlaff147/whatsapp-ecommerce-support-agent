"""Caso de uso: consultar status e itens de um pedido do cliente (UC-01, RN-02, RN-04)."""

from pawdesk.application.dto.context import CallerContext
from pawdesk.application.dto.results import OrderStatusView
from pawdesk.application.errors import NotFound
from pawdesk.application.ports.outbound.infra import Clock
from pawdesk.application.ports.outbound.repositories import OrderRepository
from pawdesk.domain.constants import VerificationLevel
from pawdesk.domain.services.delivery_eta_calculator import DeliveryEtaCalculator
from pawdesk.domain.value_objects.ids import OrderNumber


class GetOrderStatus:
    """Retorna o status do pedido validando propriedade do cliente."""

    def __init__(
        self,
        orders: OrderRepository,
        eta_calculator: DeliveryEtaCalculator,
        clock: Clock,
    ) -> None:
        self._orders = orders
        self._eta = eta_calculator
        self._clock = clock

    async def execute(self, caller: CallerContext, number: OrderNumber) -> OrderStatusView:
        caller.require(VerificationLevel.PHONE_MATCH)
        order = await self._orders.get_by_number(number)
        # Mesma resposta para inexistente e de terceiros (anti-IDOR, RN-02)
        if order is None or order.customer_id != caller.customer_id:
            raise NotFound("pedido")

        delay = self._eta.assess_delay(
            status=order.status,
            estimated_delivery_at=order.estimated_delivery_at,
            delivered_at=order.delivered_at,
            now=self._clock.now(),
        )
        return OrderStatusView.from_order(order, delay=delay)
