"""Agente auxiliar fora da árvore para resumir casos para o atendente humano."""

from google.adk.agents import LlmAgent

from pawdesk.adapters.agentic.constants import AgentName, ModelRole
from pawdesk.adapters.agentic.model_factory import ModelFactory
from pawdesk.adapters.agentic.prompts.loader import load_prompt_template


def build_case_summarizer_agent(models: ModelFactory) -> LlmAgent:
    return LlmAgent(
        name=AgentName.SUMMARIZER.value,
        description="Gera resumo objetivo de até 5 linhas para o atendente humano.",
        model=models.for_role(ModelRole.ROUTER),
        instruction=load_prompt_template("case_summarizer.md"),
    )
