"""Constantes, enums de negócio e léxicos heurísticos do domínio."""

from decimal import Decimal
from enum import IntEnum, StrEnum


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    PICKING = "PICKING"
    SHIPPED = "SHIPPED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELED = "CANCELED"


class ShipmentStatus(StrEnum):
    LABEL_CREATED = "LABEL_CREATED"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    DELAYED = "DELAYED"
    EXCEPTION = "EXCEPTION"


class ReturnReason(StrEnum):
    REGRET = "REGRET"
    DEFECTIVE = "DEFECTIVE"
    WRONG_ITEM = "WRONG_ITEM"
    DAMAGED = "DAMAGED"
    PALATABILITY = "PALATABILITY"


class ReturnIneligibility(StrEnum):
    NOT_DELIVERED = "NOT_DELIVERED"
    WINDOW_EXPIRED = "WINDOW_EXPIRED"
    ITEM_NOT_ELIGIBLE = "ITEM_NOT_ELIGIBLE"
    ALREADY_REQUESTED = "ALREADY_REQUESTED"


class ReturnStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    REFUNDED = "REFUNDED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"


class ConversationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WITH_HUMAN = "WITH_HUMAN"
    CLOSED = "CLOSED"


class MessageDirection(StrEnum):
    IN = "IN"
    OUT = "OUT"


class MessageAuthor(StrEnum):
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"


class OutboxStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class HandoffStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class HandoffPriority(StrEnum):
    NORMAL = "NORMAL"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class VerificationLevel(IntEnum):
    NONE = 0
    PHONE_MATCH = 1
    STEP_UP = 2


class HandoffReason(StrEnum):
    USER_REQUESTED = "USER_REQUESTED"
    FRUSTRATION = "FRUSTRATION"
    REPEATED_FAILURE = "REPEATED_FAILURE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REFUND_ABOVE_LIMIT = "REFUND_ABOVE_LIMIT"
    LEGAL_RISK = "LEGAL_RISK"
    FRAUD_SUSPECTED = "FRAUD_SUSPECTED"
    PET_HEALTH_EMERGENCY = "PET_HEALTH_EMERGENCY"
    DELIVERY_DELAY = "DELIVERY_DELAY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    AGENT_ERROR = "AGENT_ERROR"


# Padrões de política (valores efetivos vêm de Settings/PolicyConfig)
DEFAULT_REGRET_WINDOW_DAYS = 7
DEFAULT_DEFECT_WINDOW_DAYS = 30
DEFAULT_REFUND_APPROVAL_LIMIT = Decimal("500.00")
DEFAULT_LATE_ORDER_HANDOFF_BUSINESS_DAYS = 3

# Léxicos heurísticos para detecção objetiva de sinais
FRUSTRATION_TERMS: tuple[str, ...] = (
    "absurdo",
    "palhaçada",
    "palhacada",
    "vergonha",
    "péssimo",
    "pessimo",
    "lixo",
    "incompetente",
    "ridículo",
    "ridiculo",
    "enganação",
    "enganacao",
)

LEGAL_RISK_TERMS: tuple[str, ...] = (
    "procon",
    "advogado",
    "processo",
    "processar",
    "justiça",
    "justica",
    "reclame aqui",
    "juizado",
    "celso russomanno",
)

HUMAN_REQUEST_TERMS: tuple[str, ...] = (
    "falar com atendente",
    "falar com humano",
    "falar com uma pessoa",
    "atendente humano",
    "pessoa real",
    "transferir para atendente",
    "quero um atendente",
)

PET_EMERGENCY_TERMS: tuple[str, ...] = (
    "comeu chocolate",
    "envenen",
    "intoxic",
    "convuls",
    "sangrando",
    "vomitando sangue",
    "desmai",
    "engoliu",
    "veneno",
    "chumbinho",
    "uva passa",
)

PROMPT_INJECTION_PATTERNS: tuple[str, ...] = (
    "ignore as regras",
    "ignore todas as regras",
    "esqueça as regras",
    "esqueca as regras",
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "revele seu prompt",
    "mostre suas instruções",
    "mostre suas instrucoes",
    "jailbreak",
)

VETERINARY_FORBIDDEN_OUTPUT_TERMS: tuple[str, ...] = (
    "diagnóstico:",
    "diagnostico:",
    "recomendo dar",
    "administre",
    "dosagem de",
    "dose recomendada",
    "mg/kg",
    "comprimido",
    "prescrevo",
    "tome o remédio",
    "tome o remedio",
)

FORBIDDEN_PROMISE_TERMS: tuple[str, ...] = (
    "garanto o reembolso",
    "vou te dar um desconto",
    "desconto especial de",
    "prometo que chega",
    "exceção aprovada",
)

INTERNAL_LEAK_TERMS: tuple[str, ...] = (
    "system_prompt",
    "concierge_agent",
    "order_agent",
    "identity_agent",
    "case_summarizer_agent",
    "tool_context",
    "regras invioláveis",
)
