"""Agente especialista em pedidos, rastreio e prazo por CEP (UC-01 / UC-02)."""

from google.adk.agents import LlmAgent

from pawdesk.adapters.agentic.agents.guards import GuardCallbacks
from pawdesk.adapters.agentic.constants import AgentName, ModelRole
from pawdesk.adapters.agentic.model_factory import ModelFactory
from pawdesk.adapters.agentic.prompts.loader import make_instruction_provider
from pawdesk.adapters.agentic.tools.registry import ToolRegistry


def build_order_agent(
    models: ModelFactory,
    registry: ToolRegistry,
    guards: GuardCallbacks,
) -> LlmAgent:
    return LlmAgent(
        name=AgentName.ORDER.value,
        description=(
            "Especialista em consultar pedidos do cliente atual, status de entrega, "
            "código/link de rastreamento, atrasos e calcular prazo e frete por CEP antes da compra."
        ),
        model=models.for_role(ModelRole.SPECIALIST),
        instruction=make_instruction_provider("order.md"),
        tools=registry.for_agent(AgentName.ORDER),
        disallow_transfer_to_peers=True,
        **guards.as_kwargs(),
    )
