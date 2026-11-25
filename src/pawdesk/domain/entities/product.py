"""Entidade de Produto do catálogo pet."""

from dataclasses import dataclass

from pawdesk.domain.value_objects.money import Money


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    species: str
    category: str
    price: Money
    in_stock: bool
    weight_kg: float
    description: str = ""
