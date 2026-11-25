"""Adaptador CaseSummarizer usando agente ADK de chamada única com fallback seguro."""

import asyncio

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from pawdesk.adapters.agentic.constants import ADK_APP_NAME
from pawdesk.domain.entities.conversation import MessageView
from pawdesk.shared.utils.ids import new_ulid
from pawdesk.shared.utils.masking import redact_pii


class AdkCaseSummarizer:
    """Resume conversas para o atendente humano em até 5 linhas (com fallback determinístico)."""

    def __init__(self, summarizer_agent: LlmAgent, timeout_s: float = 8.0) -> None:
        self._agent = summarizer_agent
        self._timeout_s = timeout_s

    async def summarize(
        self,
        transcript: list[MessageView],
        *,
        reason: str,
        order_numbers: tuple[str, ...],
        max_lines: int = 5,
    ) -> str:
        if not transcript:
            return self._fallback(transcript, reason=reason, order_numbers=order_numbers)

        lines = [f"[{m.author.value}] {redact_pii(m.content_redacted)}" for m in transcript[-12:]]
        prompt = (
            f"Motivo do encaminhamento: {reason}\n"
            f"Pedidos citados: {', '.join(order_numbers) if order_numbers else 'nenhum'}\n"
            f"Máximo de linhas: {max_lines}\n\n"
            "Transcrição:\n" + "\n".join(lines)
        )

        try:
            session_service = InMemorySessionService()
            session = await session_service.create_session(
                app_name=f"{ADK_APP_NAME}_summarizer",
                user_id="system",
                session_id=new_ulid(),
            )
            runner = Runner(
                app_name=f"{ADK_APP_NAME}_summarizer",
                agent=self._agent,
                session_service=session_service,
            )
            msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

            async def _run() -> str:
                output = ""
                async for event in runner.run_async(
                    user_id="system",
                    session_id=session.id,
                    new_message=msg,
                ):
                    if event.content and event.content.parts and event.author != "user":
                        chunks = [p.text for p in event.content.parts if p.text]
                        if chunks:
                            output = "\n".join(chunks).strip()
                return output

            summary = await asyncio.wait_for(_run(), timeout=self._timeout_s)
            if summary:
                bounded = [line for line in summary.splitlines() if line.strip()][:max_lines]
                return redact_pii("\n".join(bounded))
        except Exception:
            pass

        return self._fallback(transcript, reason=reason, order_numbers=order_numbers)

    def _fallback(
        self,
        transcript: list[MessageView],
        *,
        reason: str,
        order_numbers: tuple[str, ...],
    ) -> str:
        last_customer = next(
            (m.content_redacted for m in reversed(transcript) if m.author.value == "CUSTOMER"),
            "Sem mensagem recente.",
        )
        orders_txt = ", ".join(order_numbers) if order_numbers else "nenhum"
        return (
            f"Motivo do handoff: {reason}.\n"
            f"Pedidos citados: {orders_txt}.\n"
            f"Última fala do cliente: {redact_pii(last_customer)[:180]}."
        )
