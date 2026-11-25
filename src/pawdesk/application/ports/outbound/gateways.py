"""Contratos de gateways externos (transportadora, catálogo e helpdesk)."""

from dataclasses import dataclass
from typing import Protocol

from pawdesk.application.dto.results import HandoffPackage
from pawdesk.domain.entities.product import Product
from pawdesk.domain.entities.shipment import Shipment
from pawdesk.domain.value_objects.address import ZipCode
from pawdesk.domain.value_objects.ids import OrderNumber, Sku
from pawdesk.domain.value_objects.money import Money


@dataclass(frozen=True)
class CarrierQuote:
    carrier_name: str
    business_days: int
    shipping_cost: Money


@dataclass(frozen=True)
class HelpdeskTicketCreated:
    external_ticket_id: str


class CarrierGateway(Protocol):
    async def get_tracking(self, order_number: OrderNumber) -> Shipment | None: ...
    async def estimate_by_zip(self, zip_code: ZipCode, product: Product) -> CarrierQuote: ...


class CatalogGateway(Protocol):
    async def get_by_sku(self, sku: Sku) -> Product | None: ...


class HelpdeskGateway(Protocol):
    async def create_ticket(self, package: HandoffPackage) -> HelpdeskTicketCreated: ...
    async def forward_message(
        self,
        *,
        conversation_id: str,
        external_ticket_id: str | None,
        text_redacted: str,
    ) -> None: ...
