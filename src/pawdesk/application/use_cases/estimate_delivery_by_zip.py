"""Caso de uso: estimar prazo de entrega e frete por CEP antes da compra (UC-02, RN-03)."""

from pawdesk.application.dto.results import DeliveryEstimateView
from pawdesk.application.errors import NotFound
from pawdesk.application.ports.outbound.gateways import CarrierGateway, CatalogGateway
from pawdesk.application.ports.outbound.infra import Clock
from pawdesk.domain.value_objects.address import ZipCode
from pawdesk.domain.value_objects.ids import Sku
from pawdesk.shared.utils.dates import add_business_days


class EstimateDeliveryByZip:
    """Consulta sistema de catálogo e transportadora sem nunca estimar por conta própria."""

    def __init__(
        self,
        catalog: CatalogGateway,
        carrier: CarrierGateway,
        clock: Clock,
    ) -> None:
        self._catalog = catalog
        self._carrier = carrier
        self._clock = clock

    async def execute(self, zip_code: ZipCode, sku: Sku) -> DeliveryEstimateView:
        product = await self._catalog.get_by_sku(sku)
        if product is None:
            raise NotFound("produto")

        quote = await self._carrier.estimate_by_zip(zip_code, product)
        eta = add_business_days(self._clock.now(), quote.business_days)
        return DeliveryEstimateView(
            zip_code=zip_code.formatted(),
            sku=product.sku,
            product_name=product.name,
            in_stock=product.in_stock,
            business_days=quote.business_days,
            estimated_date=eta.strftime("%d/%m/%Y"),
            shipping_cost_brl=quote.shipping_cost.format_brl(),
            carrier_name=quote.carrier_name,
        )
