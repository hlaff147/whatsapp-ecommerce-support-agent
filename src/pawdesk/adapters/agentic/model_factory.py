"""Fábrica de modelos multi-provedor (LiteLlm Anthropic/OpenAI, Gemini nativo ou FakeLlm)."""

from google.adk.models.base_llm import BaseLlm
from google.adk.models.lite_llm import LiteLlm

from pawdesk.adapters.agentic.constants import ModelRole


class ModelFactory:
    """Resolve o modelo ADK por papel de agente a partir de configuração ou overrides."""

    def __init__(
        self,
        *,
        model_router: str,
        model_specialist: str,
        model_judge: str,
        overrides: dict[ModelRole, BaseLlm] | None = None,
    ) -> None:
        self._by_role = {
            ModelRole.ROUTER: model_router,
            ModelRole.SPECIALIST: model_specialist,
            ModelRole.JUDGE: model_judge,
        }
        self._overrides = overrides or {}

    def for_role(self, role: ModelRole) -> BaseLlm | str:
        if role in self._overrides:
            return self._overrides[role]
        model_id = self._by_role[role]
        if model_id.startswith("gemini-"):
            return model_id
        return LiteLlm(model=model_id)

    def model_name(self, role: ModelRole) -> str:
        if role in self._overrides:
            return self._overrides[role].model
        return self._by_role[role]
