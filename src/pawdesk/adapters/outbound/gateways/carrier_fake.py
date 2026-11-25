"""Gateway simulado de transportadora (rastreio do MySQL + cotação determinística por CEP)."""

from decimal import Decimal

from pawdesk.application.ports.outbound.gateways import CarrierQuote
from pawdesk.application.ports.outbound.repositories import ShipmentRepository
from pawdesk.domain.entities.product import Product
from pawdesk.domain.entities.shipment import Shipment
from pawdesk.domain.value_objects.address import ZipCode
from pawdesk.domain.value_objects.ids import OrderNumber
from pawdesk.domain.value_objects.money import Money


class CarrierFakeGateway:
    """Fornece rastreamento persistido e tabela determinística de prazo/frete por CEP."""

    def __init__(self, shipments: ShipmentRepository) -> None:
        self._shipments = shipments

    async def get_tracking(self, order_number: OrderNumber) -> Shipment | None:
        return await self._shipments.get_by_order_number(order_number)

    async def estimate_by_zip(self, zip_code: ZipCode, product: Product) -> CarrierQuote:
        region_digit = int(zip_code.digits[0])
        if region_digit in {0, 1}:
            base_days, base_cost = 2, Decimal("12.90")
            carrier = "PetLog Express"
        elif region_digit in {2, 3}:
            base_days, base_cost = 4, Decimal("19.90")
            carrier = "PetLog Sudeste"
        elif region_digit in {8, 9}:
            base_days, base_cost = 5, Decimal("24.90")
            carrier = "Patas Sul Transportes"
        else:
            base_days, base_cost = 7, Decimal("29.90")
            carrier = "BrasilPet Encomendas"

        weight_surcharge = Decimal("6.00") if product.weight_kg >= 10.0 else Decimal("0.00")
        return CarrierQuote(
            carrier_name=carrier,
            business_days=base_days,
            shipping_cost=Money(base_cost + weight_surcharge),
        )
