"""Agente especialista em verificação reforçada de identidade (RN-01 Nível 2)."""

from google.adk.agents import LlmAgent

from pawdesk.adapters.agentic.agents.guards import GuardCallbacks
from pawdesk.adapters.agentic.constants import AgentName, ModelRole
from pawdesk.adapters.agentic.model_factory import ModelFactory
from pawdesk.adapters.agentic.prompts.loader import make_instruction_provider
from pawdesk.adapters.agentic.tools.registry import ToolRegistry


def build_identity_agent(
    models: ModelFactory,
    registry: ToolRegistry,
    guards: GuardCallbacks,
) -> LlmAgent:
    return LlmAgent(
        name=AgentName.IDENTITY.value,
        description=(
            "Especialista em confirmar a identidade reforçada (step-up) do cliente usando "
            "o número do pedido e os 3 últimos dígitos do CPF."
        ),
        model=models.for_role(ModelRole.ROUTER),
        instruction=make_instruction_provider("identity.md"),
        tools=registry.for_agent(AgentName.IDENTITY),
        disallow_transfer_to_peers=True,
        **guards.as_kwargs(),
    )
