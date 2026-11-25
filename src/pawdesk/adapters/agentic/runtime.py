"""Adaptador de saída AgentRuntime implementado sobre Google ADK Runner."""

import asyncio
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.genai import types

from pawdesk.adapters.agentic.constants import ADK_APP_NAME, FRAMEWORK_PASSTHROUGH_TOOLS, StateKey
from pawdesk.application.dto.agent_io import (
    AgentTurnRequest,
    AgentTurnResult,
    HandoffSignal,
    TokenUsage,
)
from pawdesk.application.errors import AgentRuntimeError
from pawdesk.shared.constants.limits import TURN_TIMEOUT_S


class AdkAgentRuntime:
    """Executa um turno conversacional sobre a árvore de agentes ADK."""

    def __init__(
        self,
        *,
        root_agent: LlmAgent,
        session_service: BaseSessionService,
        app_name: str = ADK_APP_NAME,
        default_model_name: str = "unknown",
        turn_timeout_s: float = TURN_TIMEOUT_S,
    ) -> None:
        self._root_agent = root_agent
        self._session_service = session_service
        self._app_name = app_name
        self._default_model_name = default_model_name
        self._turn_timeout_s = turn_timeout_s
        self._runner = Runner(
            app_name=app_name,
            agent=root_agent,
            session_service=session_service,
        )

    async def run_turn(self, request: AgentTurnRequest) -> AgentTurnResult:
        try:
            return await asyncio.wait_for(
                self._execute_turn(request),
                timeout=self._turn_timeout_s,
            )
        except AgentRuntimeError:
            raise
        except Exception as exc:
            raise AgentRuntimeError(f"Falha no runtime ADK: {exc}") from exc

    async def _execute_turn(self, request: AgentTurnRequest) -> AgentTurnResult:
        session = await self._session_service.get_session(
            app_name=self._app_name,
            user_id=request.user_id,
            session_id=request.session_id,
        )
        if session is None:
            session = await self._session_service.create_session(
                app_name=self._app_name,
                user_id=request.user_id,
                session_id=request.session_id,
                state={StateKey.LOCALE.value: request.locale},
            )

        state_delta: dict[str, Any] = {
            StateKey.CUSTOMER_ID.value: (
                request.caller.customer_id.value if request.caller.customer_id else None
            ),
            StateKey.CUSTOMER_FIRST_NAME.value: request.caller.customer_first_name or "cliente",
            StateKey.VERIFICATION_LEVEL.value: int(request.caller.level),
            StateKey.CONVERSATION_ID.value: request.caller.conversation_id,
            StateKey.CORRELATION_ID.value: request.caller.correlation_id,
            StateKey.CONFIRMED_ACTION_ID.value: request.confirmed_action_id,
            StateKey.TOOL_CALLS_IN_TURN.value: 0,
            StateKey.LLM_CALLS_IN_TURN.value: 0,
            StateKey.TOOLS_CALLED_IN_TURN.value: [],
            StateKey.HANDOFF_REQUESTED.value: None,
            StateKey.LATE_ORDER_HANDOFF.value: False,
            StateKey.TOOL_ERROR_COUNT.value: request.tool_error_count,
            StateKey.FALLBACK_COUNT.value: request.fallback_count,
            StateKey.VERIFICATION_ATTEMPTS.value: request.verification_attempts,
            StateKey.LOCALE.value: request.locale,
        }

        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=request.text or " ")],
        )

        reply_text = ""
        last_agent_name: str | None = None
        tools_from_events: list[str] = []
        usage_list: list[TokenUsage] = []

        async for event in self._runner.run_async(
            user_id=request.user_id,
            session_id=request.session_id,
            new_message=message,
            state_delta=state_delta,
        ):
            if event.author and event.author != "user":
                last_agent_name = event.author

            if event.content and event.content.parts:
                text_chunks = [part.text for part in event.content.parts if part.text]
                if text_chunks and event.author != "user":
                    reply_text = "\n".join(text_chunks).strip()

                for part in event.content.parts:
                    if part.function_call and part.function_call.name:
                        name = part.function_call.name
                        if name not in FRAMEWORK_PASSTHROUGH_TOOLS:
                            tools_from_events.append(name)

            if event.usage_metadata is not None:
                in_tokens = int(getattr(event.usage_metadata, "prompt_token_count", 0) or 0)
                out_tokens = int(getattr(event.usage_metadata, "candidates_token_count", 0) or 0)
                if in_tokens > 0 or out_tokens > 0:
                    model_ver = str(event.model_version or self._default_model_name)
                    usage_list.append(
                        TokenUsage(
                            model=model_ver,
                            input_tokens=in_tokens,
                            output_tokens=out_tokens,
                        )
                    )

        updated_session = await self._session_service.get_session(
            app_name=self._app_name,
            user_id=request.user_id,
            session_id=request.session_id,
        )
        final_state = updated_session.state if updated_session is not None else {}

        handoff_raw = final_state.get(StateKey.HANDOFF_REQUESTED.value)
        handoff_signal = (
            HandoffSignal(
                reason=str(handoff_raw.get("reason", "OUT_OF_SCOPE")),
                note=str(handoff_raw.get("note", "")),
            )
            if isinstance(handoff_raw, dict)
            else None
        )

        tools_in_state = final_state.get(StateKey.TOOLS_CALLED_IN_TURN.value, [])
        all_tools = tuple(dict.fromkeys([*tools_from_events, *[str(t) for t in tools_in_state]]))

        return AgentTurnResult(
            reply_text=reply_text,
            agent_name=last_agent_name,
            handoff=handoff_signal,
            tools_called=all_tools,
            usage=tuple(usage_list),
            trace_id=request.caller.correlation_id,
            fallback_count=int(final_state.get(StateKey.FALLBACK_COUNT.value, 0)),
            tool_error_count=int(final_state.get(StateKey.TOOL_ERROR_COUNT.value, 0)),
            late_order_requires_handoff=bool(
                final_state.get(StateKey.LATE_ORDER_HANDOFF.value, False)
            ),
        )
