"""Entidade de Solicitação de Troca/Devolução (base preparada para Fase 5)."""

from dataclasses import dataclass
from datetime import datetime

from pawdesk.domain.constants import ReturnReason, ReturnStatus
from pawdesk.domain.value_objects.ids import ConversationId, OrderNumber
from pawdesk.domain.value_objects.money import Money


@dataclass(frozen=True)
class ReturnRequest:
    id: str
    action_id: str
    conversation_id: ConversationId
    order_number: OrderNumber
    item_sku: str
    reason: ReturnReason
    details: str
    status: ReturnStatus
    refund_amount: Money | None
    protocol: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
