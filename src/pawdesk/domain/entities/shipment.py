"""Entidades de Entrega / Rastreio (Shipment e ShipmentEvent)."""

from dataclasses import dataclass
from datetime import datetime

from pawdesk.domain.constants import ShipmentStatus
from pawdesk.domain.value_objects.ids import OrderNumber
from pawdesk.domain.value_objects.tracking_code import TrackingCode


@dataclass(frozen=True)
class ShipmentEvent:
    occurred_at: datetime
    status: str
    location: str
    description: str


@dataclass(frozen=True)
class Shipment:
    order_number: OrderNumber
    carrier_name: str
    tracking_code: TrackingCode
    tracking_url: str
    status: ShipmentStatus
    estimated_delivery_at: datetime | None
    delivered_at: datetime | None = None
    events: tuple[ShipmentEvent, ...] = ()

    @property
    def latest_event(self) -> ShipmentEvent | None:
        if not self.events:
            return None
        return max(self.events, key=lambda event: event.occurred_at)
