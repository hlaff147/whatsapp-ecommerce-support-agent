"""Política de cálculo de prazo e detecção de atraso (RN-03 e RN-04)."""

from dataclasses import dataclass
from datetime import datetime

from pawdesk.domain.constants import DEFAULT_LATE_ORDER_HANDOFF_BUSINESS_DAYS, OrderStatus
from pawdesk.shared.utils.dates import business_days_between, to_local


@dataclass(frozen=True)
class DeliveryDelayAssessment:
    is_late: bool
    late_business_days: int
    requires_handoff: bool


class DeliveryEtaCalculator:
    """Avalia atraso de pedidos existentes usando relógio injetado (RN-04)."""

    def __init__(
        self, handoff_threshold_business_days: int = DEFAULT_LATE_ORDER_HANDOFF_BUSINESS_DAYS
    ) -> None:
        self._threshold_days = handoff_threshold_business_days

    def assess_delay(
        self,
        *,
        status: OrderStatus,
        estimated_delivery_at: datetime | None,
        delivered_at: datetime | None,
        now: datetime,
    ) -> DeliveryDelayAssessment:
        """Determina se um pedido ativo está atrasado e se excede o limite de handoff."""
        if (
            estimated_delivery_at is None
            or delivered_at is not None
            or status in {OrderStatus.DELIVERED, OrderStatus.CANCELED}
        ):
            return DeliveryDelayAssessment(
                is_late=False, late_business_days=0, requires_handoff=False
            )

        local_now = to_local(now)
        local_eta = to_local(estimated_delivery_at)
        if local_now <= local_eta:
            return DeliveryDelayAssessment(
                is_late=False, late_business_days=0, requires_handoff=False
            )

        late_bdays = business_days_between(local_eta, local_now)
        # Mesmo se atrasou no mesmo dia após o horário previsto, já é reconhecido como atrasado
        is_late = True
        requires_handoff = late_bdays > self._threshold_days
        return DeliveryDelayAssessment(
            is_late=is_late,
            late_business_days=late_bdays,
            requires_handoff=requires_handoff,
        )
