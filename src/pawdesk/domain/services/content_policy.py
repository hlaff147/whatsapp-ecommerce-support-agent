"""Política de segurança e conformidade de conteúdo de entrada e saída (RN-13, RN-14, RN-17)."""

from dataclasses import dataclass

from pawdesk.domain.constants import (
    FORBIDDEN_PROMISE_TERMS,
    INTERNAL_LEAK_TERMS,
    PET_EMERGENCY_TERMS,
    PROMPT_INJECTION_PATTERNS,
    VETERINARY_FORBIDDEN_OUTPUT_TERMS,
)
from pawdesk.shared.constants.regex import CPF_RE


@dataclass(frozen=True)
class InputInspection:
    is_prompt_injection: bool = False
    is_pet_emergency: bool = False


@dataclass(frozen=True)
class OutputInspection:
    allowed: bool
    violation: str | None = None


class ContentPolicy:
    """Inspeciona textos de entrada e saída contra violações de política."""

    def inspect_input(self, text: str) -> InputInspection:
        lower = text.lower()
        return InputInspection(
            is_prompt_injection=any(pattern in lower for pattern in PROMPT_INJECTION_PATTERNS),
            is_pet_emergency=any(term in lower for term in PET_EMERGENCY_TERMS),
        )

    def inspect_output(self, text: str) -> OutputInspection:
        lower = text.lower()
        if any(term in lower for term in VETERINARY_FORBIDDEN_OUTPUT_TERMS):
            return OutputInspection(allowed=False, violation="VETERINARY_ADVICE")
        if any(term in lower for term in FORBIDDEN_PROMISE_TERMS):
            return OutputInspection(allowed=False, violation="FORBIDDEN_PROMISE")
        if any(term in lower for term in INTERNAL_LEAK_TERMS):
            return OutputInspection(allowed=False, violation="INTERNAL_LEAK")
        if CPF_RE.search(text):
            return OutputInspection(allowed=False, violation="PII_CPF_LEAK")
        return OutputInspection(allowed=True)
