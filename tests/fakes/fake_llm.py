"""Implementação determinística de BaseLlm do Google ADK para testes sem rede."""

from collections.abc import AsyncGenerator, Callable
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr


def text_response(
    text: str,
    *,
    input_tokens: int = 50,
    output_tokens: int = 20,
) -> LlmResponse:
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part.from_text(text=text)]),
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=input_tokens,
            candidates_token_count=output_tokens,
        ),
    )


def tool_call_response(
    name: str,
    args: dict[str, Any],
    *,
    input_tokens: int = 60,
    output_tokens: int = 25,
) -> LlmResponse:
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_function_call(name=name, args=args)],
        ),
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=input_tokens,
            candidates_token_count=output_tokens,
        ),
    )


class ScriptedFakeLlm(BaseLlm):
    """LLM falso roteirizado compatível com ADK Runner sem chamadas de rede."""

    model: str = "fake-llm"
    _queue: list[LlmResponse] = PrivateAttr(default_factory=list)
    _handler: Callable[[LlmRequest], LlmResponse] | None = PrivateAttr(default=None)
    _requests: list[LlmRequest] = PrivateAttr(default_factory=list)

    def __init__(
        self,
        responses: list[LlmResponse] | None = None,
        *,
        handler: Callable[[LlmRequest], LlmResponse] | None = None,
        model: str = "fake-llm",
    ) -> None:
        super().__init__(model=model)
        self._queue = list(responses or [])
        self._handler = handler
        self._requests = []

    @property
    def requests(self) -> list[LlmRequest]:
        return self._requests

    def push(self, *responses: LlmResponse) -> None:
        self._queue.extend(responses)

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        _ = stream
        self._requests.append(llm_request)
        if self._queue:
            yield self._queue.pop(0)
            return
        if self._handler is not None:
            yield self._handler(llm_request)
            return
        yield text_response("Resposta padrão de teste.")
