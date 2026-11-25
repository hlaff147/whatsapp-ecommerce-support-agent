"""Cálculo de custo em USD a partir do uso de tokens por modelo."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from pawdesk.application.dto.agent_io import TokenUsage


@dataclass(frozen=True)
class ModelPricing:
    input_per_1m_usd: Decimal
    output_per_1m_usd: Decimal


_MILLION = Decimal("1000000")


class CostService:
    """Converte métricas de tokens em custo USD usando tabela configurável."""

    def __init__(
        self,
        pricing_by_model: dict[str, ModelPricing] | None = None,
        default_pricing: ModelPricing | None = None,
    ) -> None:
        self._pricing = pricing_by_model or {}
        self._default = default_pricing or ModelPricing(
            input_per_1m_usd=Decimal("0.80"),
            output_per_1m_usd=Decimal("4.00"),
        )

    def calculate_usd(self, usage: tuple[TokenUsage, ...]) -> Decimal:
        total = Decimal("0")
        for item in usage:
            price = self._pricing.get(item.model, self._default)
            in_cost = (Decimal(item.input_tokens) / _MILLION) * price.input_per_1m_usd
            out_cost = (Decimal(item.output_tokens) / _MILLION) * price.output_per_1m_usd
            total += in_cost + out_cost
        return total.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
