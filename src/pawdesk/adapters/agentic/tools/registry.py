"""Registro central de tools: mapeia permissões mínimas e atribuição por agente."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset

from pawdesk.adapters.agentic.constants import AgentName, ToolName
from pawdesk.domain.constants import VerificationLevel


@dataclass(frozen=True)
class ToolSpec:
    name: ToolName
    fn: Callable[..., Any]
    min_level: VerificationLevel
    agents: tuple[AgentName, ...]
    has_side_effect: bool = False


class ToolRegistry:
    """Fonte única de verdade sobre quais tools cada agente possui e seu nível mínimo."""

    def __init__(self, specs: list[ToolSpec]) -> None:
        self._by_name: dict[str, ToolSpec] = {s.name.value: s for s in specs}
        self._specs = specs

    def find(self, tool_name: str) -> ToolSpec | None:
        return self._by_name.get(tool_name)

    def spec_for(self, tool_name: str) -> ToolSpec:
        return self._by_name[tool_name]

    def for_agent(self, agent: AgentName) -> list[Callable[..., Any] | BaseTool | BaseToolset]:
        return [s.fn for s in self._specs if agent in s.agents]
