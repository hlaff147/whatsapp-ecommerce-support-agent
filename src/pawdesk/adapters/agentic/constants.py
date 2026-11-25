"""Constantes de nomes de agentes, tools, chaves de estado e papéis de modelo."""

from enum import StrEnum

ADK_APP_NAME = "pawdesk"

FRAMEWORK_PASSTHROUGH_TOOLS: frozenset[str] = frozenset({"transfer_to_agent"})


class AgentName(StrEnum):
    CONCIERGE = "concierge_agent"
    IDENTITY = "identity_agent"
    ORDER = "order_agent"
    SUMMARIZER = "case_summarizer_agent"


class ToolName(StrEnum):
    VERIFY_IDENTITY = "verify_customer_identity"
    GET_MY_ORDERS = "get_my_orders"
    GET_ORDER_STATUS = "get_order_status"
    TRACK_SHIPMENT = "track_shipment"
    ESTIMATE_DELIVERY_BY_ZIP = "estimate_delivery_by_zip"
    REQUEST_HANDOFF = "request_human_handoff"


class StateKey(StrEnum):
    CUSTOMER_ID = "customer_id"
    CUSTOMER_FIRST_NAME = "customer_first_name"
    VERIFICATION_LEVEL = "verification_level"
    CONVERSATION_ID = "conversation_id"
    CORRELATION_ID = "correlation_id"
    ACTIVE_ORDER_NUMBER = "active_order_number"
    PENDING_ACTION = "pending_action"
    CONFIRMED_ACTION_ID = "confirmed_action_id"
    HANDOFF_REQUESTED = "handoff_requested"
    LATE_ORDER_HANDOFF = "late_order_handoff"
    FALLBACK_COUNT = "fallback_count"
    TOOL_ERROR_COUNT = "tool_error_count"
    VERIFICATION_ATTEMPTS = "verification_attempts"
    TOOL_CALLS_IN_TURN = "tool_calls_in_turn"
    LLM_CALLS_IN_TURN = "llm_calls_in_turn"
    TOOLS_CALLED_IN_TURN = "tools_called_in_turn"
    LOCALE = "user:locale"


class ModelRole(StrEnum):
    ROUTER = "router"
    SPECIALIST = "specialist"
    JUDGE = "judge"
