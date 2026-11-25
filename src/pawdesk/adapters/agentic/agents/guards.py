"""Estrutura compartilhada de callbacks para todos os agentes da árvore."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GuardCallbacks:
    before_model: Callable[..., Any]
    after_model: Callable[..., Any]
    before_tool: Callable[..., Any]
    after_tool: Callable[..., Any]

    def as_kwargs(self) -> dict[str, Any]:
        return {
            "before_model_callback": self.before_model,
            "after_model_callback": self.after_model,
            "before_tool_callback": self.before_tool,
            "after_tool_callback": self.after_tool,
        }
