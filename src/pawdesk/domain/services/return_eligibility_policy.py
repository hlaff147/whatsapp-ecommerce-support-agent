"""Política pura de elegibilidade para troca/devolução (RN-05 a RN-08)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from pawdesk.domain.constants import (
    DEFAULT_DEFECT_WINDOW_DAYS,
    DEFAULT_REGRET_WINDOW_DAYS,
    ReturnIneligibility,
    ReturnReason,
)
from pawdesk.domain.entities.order import Order, OrderItem


@dataclass(frozen=True)
class PolicyConfig:
    regret_window_days: int = DEFAULT_REGRET_WINDOW_DAYS
    defect_window_days: int = DEFAULT_DEFECT_WINDOW_DAYS


@dataclass(frozen=True)
class EligibilityDecision:
    eligible: bool
    reason: ReturnIneligibility | None = None
    deadline: datetime | None = None


class ReturnEligibilityPolicy:
    """Regra pura de elegibilidade: sem I/O nem relógio global."""

    _DEFECT_REASONS = frozenset(
        {ReturnReason.DEFECTIVE, ReturnReason.DAMAGED, ReturnReason.WRONG_ITEM}
    )

    def __init__(self, config: PolicyConfig) -> None:
        self._cfg = config

    def evaluate(
        self,
        *,
        order: Order,
        item: OrderItem,
        reason: ReturnReason,
        already_requested: bool,
        now: datetime,
    ) -> EligibilityDecision:
        if order.delivered_at is None:
            return EligibilityDecision(False, ReturnIneligibility.NOT_DELIVERED)
        if already_requested:
            return EligibilityDecision(False, ReturnIneligibility.ALREADY_REQUESTED)
        if not item.returnable:
            return EligibilityDecision(False, ReturnIneligibility.ITEM_NOT_ELIGIBLE)

        days = (
            self._cfg.defect_window_days
            if reason in self._DEFECT_REASONS
            else self._cfg.regret_window_days
        )
        deadline = order.delivered_at + timedelta(days=days)
        if now > deadline:
            return EligibilityDecision(False, ReturnIneligibility.WINDOW_EXPIRED, deadline)
        return EligibilityDecision(True, None, deadline)
