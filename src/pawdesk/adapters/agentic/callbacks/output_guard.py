"""Guardrail de saída (`after_model_callback`): aplica ContentPolicy e redação de PII."""

from collections.abc import Callable

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from pawdesk.application.messages import Messages
from pawdesk.application.ports.outbound.telemetry import Telemetry
from pawdesk.domain.services.content_policy import ContentPolicy
from pawdesk.shared.utils.masking import redact_pii


def make_after_model_callback(
    *,
    content_policy: ContentPolicy,
    messages: Messages,
    telemetry: Telemetry,
) -> Callable[[CallbackContext, LlmResponse], LlmResponse | None]:
    """Constrói after_model_callback compartilhado entre todos os agentes."""

    def after_model_callback(
        callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        _ = callback_context
        if llm_response.content is None or not llm_response.content.parts:
            return None

        text_parts = [part.text for part in llm_response.content.parts if part.text]
        if not text_parts:
            return None

        combined = "\n".join(text_parts)
        inspection = content_policy.inspect_output(combined)
        if not inspection.allowed:
            telemetry.increment_guardrail_trigger(
                f"output_{(inspection.violation or 'policy').lower()}"
            )
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=messages.output_guard_fallback)],
                )
            )

        redacted = redact_pii(combined)
        if redacted != combined:
            telemetry.increment_guardrail_trigger("output_pii_redacted")
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=redacted)],
                )
            )

        return None

    return after_model_callback
