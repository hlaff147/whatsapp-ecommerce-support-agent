"""Visões de saída dos casos de uso (com minimização de dados para o LLM)."""

from dataclasses import dataclass
from datetime import datetime

from pawdesk.domain.constants import HandoffPriority, HandoffReason, OrderStatus, VerificationLevel
from pawdesk.domain.entities.order import Order
from pawdesk.domain.entities.shipment import Shipment
from pawdesk.domain.services.delivery_eta_calculator import DeliveryDelayAssessment
from pawdesk.shared.utils.dates import to_local


def _fmt_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return to_local(dt).strftime("%d/%m/%Y %H:%M")


@dataclass(frozen=True)
class OrderSummaryView:
    order_number: str
    status: OrderStatus
    total_brl: str
    placed_at: str
    estimated_delivery_at: str | None
    items_preview: tuple[str, ...]

    @classmethod
    def from_order(cls, order: Order) -> "OrderSummaryView":
        return cls(
            order_number=order.number.value,
            status=order.status,
            total_brl=order.total.format_brl(),
            placed_at=to_local(order.placed_at).strftime("%d/%m/%Y"),
            estimated_delivery_at=_fmt_dt(order.estimated_delivery_at),
            items_preview=tuple(f"{item.name} (x{item.quantity})" for item in order.items[:3]),
        )

    def to_llm_view(self) -> dict[str, object]:
        return {
            "order_number": self.order_number,
            "status": self.status.value,
            "total": self.total_brl,
            "placed_at": self.placed_at,
            "estimated_delivery": self.estimated_delivery_at,
            "items": list(self.items_preview),
        }


@dataclass(frozen=True)
class OrderStatusView:
    order_number: str
    status: OrderStatus
    total_brl: str
    placed_at: str
    estimated_delivery_at: str | None
    delivered_at: str | None
    items: tuple[dict[str, object], ...]
    delay: DeliveryDelayAssessment

    @classmethod
    def from_order(cls, order: Order, delay: DeliveryDelayAssessment) -> "OrderStatusView":
        return cls(
            order_number=order.number.value,
            status=order.status,
            total_brl=order.total.format_brl(),
            placed_at=_fmt_dt(order.placed_at) or "",
            estimated_delivery_at=_fmt_dt(order.estimated_delivery_at),
            delivered_at=_fmt_dt(order.delivered_at),
            items=tuple(
                {
                    "sku": item.sku,
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price.format_brl(),
                }
                for item in order.items
            ),
            delay=delay,
        )

    def to_llm_view(self) -> dict[str, object]:
        return {
            "order_number": self.order_number,
            "status": self.status.value,
            "total": self.total_brl,
            "placed_at": self.placed_at,
            "estimated_delivery": self.estimated_delivery_at,
            "delivered_at": self.delivered_at,
            "items": list(self.items),
            "is_late": self.delay.is_late,
            "late_business_days": self.delay.late_business_days,
            "requires_handoff": self.delay.requires_handoff,
        }


@dataclass(frozen=True)
class ShipmentTrackingView:
    order_number: str
    carrier_name: str
    tracking_code: str
    tracking_url: str
    status: str
    estimated_delivery_at: str | None
    delivered_at: str | None
    latest_event: dict[str, str] | None
    events: tuple[dict[str, str], ...]
    delay: DeliveryDelayAssessment

    @classmethod
    def from_shipment(
        cls, shipment: Shipment, delay: DeliveryDelayAssessment
    ) -> "ShipmentTrackingView":
        latest = shipment.latest_event
        latest_dict = (
            {
                "occurred_at": _fmt_dt(latest.occurred_at) or "",
                "status": latest.status,
                "location": latest.location,
                "description": latest.description,
            }
            if latest
            else None
        )
        ordered_events = tuple(
            {
                "occurred_at": _fmt_dt(ev.occurred_at) or "",
                "status": ev.status,
                "location": ev.location,
                "description": ev.description,
            }
            for ev in sorted(shipment.events, key=lambda e: e.occurred_at, reverse=True)[:5]
        )
        return cls(
            order_number=shipment.order_number.value,
            carrier_name=shipment.carrier_name,
            tracking_code=shipment.tracking_code.value,
            tracking_url=shipment.tracking_url,
            status=shipment.status.value,
            estimated_delivery_at=_fmt_dt(shipment.estimated_delivery_at),
            delivered_at=_fmt_dt(shipment.delivered_at),
            latest_event=latest_dict,
            events=ordered_events,
            delay=delay,
        )

    def to_llm_view(self) -> dict[str, object]:
        return {
            "order_number": self.order_number,
            "carrier": self.carrier_name,
            "tracking_code": self.tracking_code,
            "tracking_url": self.tracking_url,
            "status": self.status,
            "estimated_delivery": self.estimated_delivery_at,
            "delivered_at": self.delivered_at,
            "latest_event": self.latest_event,
            "recent_events": list(self.events),
            "is_late": self.delay.is_late,
            "late_business_days": self.delay.late_business_days,
            "requires_handoff": self.delay.requires_handoff,
        }


@dataclass(frozen=True)
class DeliveryEstimateView:
    zip_code: str
    sku: str
    product_name: str
    in_stock: bool
    business_days: int
    estimated_date: str
    shipping_cost_brl: str
    carrier_name: str

    def to_llm_view(self) -> dict[str, object]:
        return {
            "zip_code": self.zip_code,
            "sku": self.sku,
            "product_name": self.product_name,
            "in_stock": self.in_stock,
            "business_days": self.business_days,
            "estimated_date": self.estimated_date,
            "shipping_cost": self.shipping_cost_brl,
            "carrier": self.carrier_name,
        }


@dataclass(frozen=True)
class VerificationView:
    verified: bool
    verification_level: VerificationLevel
    attempts_remaining: int
    blocked: bool
    should_handoff: bool
    message: str

    def to_llm_view(self) -> dict[str, object]:
        return {
            "verified": self.verified,
            "verification_level": int(self.verification_level),
            "attempts_remaining": self.attempts_remaining,
            "blocked": self.blocked,
            "should_handoff": self.should_handoff,
            "message": self.message,
        }


@dataclass(frozen=True)
class HandoffPackage:
    conversation_id: str
    summary: str
    customer_first_name: str | None
    verification_level: VerificationLevel
    order_numbers: tuple[str, ...]
    actions_executed: tuple[str, ...]
    reason: HandoffReason
    priority: HandoffPriority
    urgent: bool
    sentiment: str
    suggested_next_steps: str


@dataclass(frozen=True)
class OutboundMessage:
    id: str
    conversation_id: str
    recipient_phone: str
    text: str
    ui_hint: dict[str, object] | None
    created_at: datetime
