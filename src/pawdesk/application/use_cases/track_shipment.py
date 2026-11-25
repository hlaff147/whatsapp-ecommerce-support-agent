"""Caso de uso: rastrear entrega e avaliar atraso (UC-01, RN-02, RN-04)."""

from pawdesk.application.dto.context import CallerContext
from pawdesk.application.dto.results import ShipmentTrackingView
from pawdesk.application.errors import NotFound
from pawdesk.application.ports.outbound.gateways import CarrierGateway
from pawdesk.application.ports.outbound.infra import Clock
from pawdesk.application.ports.outbound.repositories import OrderRepository
from pawdesk.domain.constants import VerificationLevel
from pawdesk.domain.services.delivery_eta_calculator import DeliveryEtaCalculator
from pawdesk.domain.value_objects.ids import OrderNumber


class TrackShipment:
    """Consulta rastreamento da entrega validando posse do pedido."""

    def __init__(
        self,
        orders: OrderRepository,
        carrier: CarrierGateway,
        eta_calculator: DeliveryEtaCalculator,
        clock: Clock,
    ) -> None:
        self._orders = orders
        self._carrier = carrier
        self._eta = eta_calculator
        self._clock = clock

    async def execute(self, caller: CallerContext, number: OrderNumber) -> ShipmentTrackingView:
        caller.require(VerificationLevel.PHONE_MATCH)
        order = await self._orders.get_by_number(number)
        if order is None or order.customer_id != caller.customer_id:
            raise NotFound("pedido")

        shipment = await self._carrier.get_tracking(number)
        if shipment is None:
            raise NotFound("rastreamento")

        delay = self._eta.assess_delay(
            status=order.status,
            estimated_delivery_at=shipment.estimated_delivery_at or order.estimated_delivery_at,
            delivered_at=shipment.delivered_at or order.delivered_at,
            now=self._clock.now(),
        )
        return ShipmentTrackingView.from_shipment(shipment, delay=delay)
