"""Fábrica da árvore completa de agentes do MVP."""

from google.adk.agents import LlmAgent

from pawdesk.adapters.agentic.agents.concierge import build_concierge_agent
from pawdesk.adapters.agentic.agents.guards import GuardCallbacks
from pawdesk.adapters.agentic.agents.identity import build_identity_agent
from pawdesk.adapters.agentic.agents.order import build_order_agent
from pawdesk.adapters.agentic.model_factory import ModelFactory
from pawdesk.adapters.agentic.tools.registry import ToolRegistry


def build_agent_tree(
    models: ModelFactory,
    registry: ToolRegistry,
    guards: GuardCallbacks,
) -> LlmAgent:
    """Constrói o root agent com subagentes especialistas e guardrails compartilhados."""
    order_agent = build_order_agent(models, registry, guards)
    identity_agent = build_identity_agent(models, registry, guards)
    return build_concierge_agent(
        models,
        registry,
        guards,
        sub_agents=[order_agent, identity_agent],
    )
