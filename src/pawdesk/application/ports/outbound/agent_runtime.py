"""Portas do runtime agêntico e do sumarizador de casos."""

from typing import Protocol

from pawdesk.application.dto.agent_io import AgentTurnRequest, AgentTurnResult
from pawdesk.domain.entities.conversation import MessageView


class AgentRuntime(Protocol):
    async def run_turn(self, request: AgentTurnRequest) -> AgentTurnResult: ...


class CaseSummarizer(Protocol):
    async def summarize(
        self,
        transcript: list[MessageView],
        *,
        reason: str,
        order_numbers: tuple[str, ...],
        max_lines: int = 5,
    ) -> str: ...
