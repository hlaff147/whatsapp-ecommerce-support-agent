"""Guardrail de entrada (`before_model_callback`): tamanho, injeção, emergência e orçamento."""

from collections.abc import Callable

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from pawdesk.adapters.agentic.constants import StateKey
from pawdesk.application.messages import Messages
from pawdesk.application.ports.outbound.telemetry import Telemetry
from pawdesk.domain.constants import HandoffReason
from pawdesk.domain.services.content_policy import ContentPolicy
from pawdesk.shared.constants.limits import MAX_INPUT_CHARS, MAX_LLM_CALLS_PER_TURN


def _safe_response(text: str) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part.from_text(text=text)]))


def _extract_latest_user_text(llm_request: LlmRequest) -> str:
    if not llm_request.contents:
        return ""
    last = llm_request.contents[-1]
    if last.role != "user" or not last.parts:
        return ""
    texts = [part.text for part in last.parts if part.text]
    return "\n".join(texts)


def _truncate_latest_user_text(llm_request: LlmRequest, max_chars: int) -> None:
    if not llm_request.contents:
        return
    last = llm_request.contents[-1]
    if last.role != "user" or not last.parts:
        return
    for part in last.parts:
        if part.text and len(part.text) > max_chars:
            part.text = part.text[:max_chars]


def make_before_model_callback(
    *,
    content_policy: ContentPolicy,
    messages: Messages,
    telemetry: Telemetry,
    vet_channel_available: bool,
) -> Callable[[CallbackContext, LlmRequest], LlmResponse | None]:
    """Constrói before_model_callback compartilhado entre todos os agentes."""

    def before_model_callback(
        callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        state = callback_context.state
        llm_calls = int(state.get(StateKey.LLM_CALLS_IN_TURN.value, 0)) + 1
        state[StateKey.LLM_CALLS_IN_TURN.value] = llm_calls

        if llm_calls > MAX_LLM_CALLS_PER_TURN:
            state[StateKey.HANDOFF_REQUESTED.value] = {
                "reason": HandoffReason.REPEATED_FAILURE.value,
                "note": "orçamento de chamadas ao LLM por turno excedido",
            }
            telemetry.increment_guardrail_trigger("llm_budget_exceeded")
            return _safe_response(messages.agent_error)

        user_text = _extract_latest_user_text(llm_request)
        if not user_text:
            return None

        if len(user_text) > MAX_INPUT_CHARS:
            _truncate_latest_user_text(llm_request, MAX_INPUT_CHARS)
            user_text = user_text[:MAX_INPUT_CHARS]

        inspection = content_policy.inspect_input(user_text)
        if inspection.is_pet_emergency:
            state[StateKey.HANDOFF_REQUESTED.value] = {
                "reason": HandoffReason.PET_HEALTH_EMERGENCY.value,
                "note": "emergência de saúde pet detectada na entrada",
            }
            telemetry.increment_guardrail_trigger("pet_emergency")
            text = (
                messages.pet_emergency_with_vet_channel
                if vet_channel_available
                else messages.pet_emergency_base
            )
            return _safe_response(text)

        if inspection.is_prompt_injection:
            telemetry.increment_guardrail_trigger("prompt_injection")
            return _safe_response(messages.prompt_injection_deflection)

        return None

    return before_model_callback
