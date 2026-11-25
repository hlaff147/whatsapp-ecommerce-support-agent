"""Agente roteador principal (root agent) do PawDesk."""

from google.adk.agents import LlmAgent

from pawdesk.adapters.agentic.agents.guards import GuardCallbacks
from pawdesk.adapters.agentic.constants import AgentName, ModelRole
from pawdesk.adapters.agentic.model_factory import ModelFactory
from pawdesk.adapters.agentic.prompts.loader import make_instruction_provider
from pawdesk.adapters.agentic.tools.registry import ToolRegistry


def build_concierge_agent(
    models: ModelFactory,
    registry: ToolRegistry,
    guards: GuardCallbacks,
    *,
    sub_agents: list[LlmAgent],
) -> LlmAgent:
    return LlmAgent(
        name=AgentName.CONCIERGE.value,
        description="Roteador principal de atendimento ao cliente do PawDesk.",
        model=models.for_role(ModelRole.ROUTER),
        instruction=make_instruction_provider("concierge.md"),
        tools=registry.for_agent(AgentName.CONCIERGE),
        sub_agents=list(sub_agents),
        **guards.as_kwargs(),
    )
