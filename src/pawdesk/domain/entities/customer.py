"""Entidade Customer (minimização LGPD: nunca armazena CPF completo)."""

from dataclasses import dataclass

from pawdesk.domain.value_objects.ids import CustomerId
from pawdesk.domain.value_objects.phone import PhoneE164


@dataclass(frozen=True)
class Customer:
    id: CustomerId
    first_name: str
    phone: PhoneE164
    cpf_last3: str
    cpf_hash: str
