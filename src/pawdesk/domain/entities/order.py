"""Entidades de Pedido e Item de Pedido."""

from dataclasses import dataclass
from datetime import datetime

from pawdesk.domain.constants import OrderStatus
from pawdesk.domain.value_objects.ids import CustomerId, OrderNumber
from pawdesk.domain.value_objects.money import Money


@dataclass(frozen=True)
class OrderItem:
    sku: str
    name: str
    quantity: int
    unit_price: Money
    category: str
    returnable: bool = True


@dataclass(frozen=True)
class Order:
    number: OrderNumber
    customer_id: CustomerId
    status: OrderStatus
    items: tuple[OrderItem, ...]
    total: Money
    placed_at: datetime
    delivered_at: datetime | None = None
    estimated_delivery_at: datetime | None = None

    def find_item(self, sku: str) -> OrderItem | None:
        normalized = sku.strip().upper()
        return next((item for item in self.items if item.sku.upper() == normalized), None)
