"""Carregamento seguro de prompts versionados via InstructionProvider."""

from collections.abc import Callable
from pathlib import Path

from google.adk.agents.readonly_context import ReadonlyContext

from pawdesk.adapters.agentic.constants import StateKey

_PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt_template(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def make_instruction_provider(filename: str) -> Callable[[ReadonlyContext], str]:
    """Cria um InstructionProvider que interpola chaves conhecidas do estado com fallback seguro."""
    template = load_prompt_template(filename)

    def _provide(ctx: ReadonlyContext) -> str:
        state = ctx.state
        first_name = str(state.get(StateKey.CUSTOMER_FIRST_NAME.value) or "cliente")
        verif_level = str(state.get(StateKey.VERIFICATION_LEVEL.value, 0))
        active_order = str(state.get(StateKey.ACTIVE_ORDER_NUMBER.value) or "nenhum")
        return (
            template.replace("{customer_first_name}", first_name)
            .replace("{verification_level}", verif_level)
            .replace("{active_order_number}", active_order)
        )

    return _provide
