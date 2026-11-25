"""Value Object de CEP e endereço resumido."""

from dataclasses import dataclass

from pawdesk.domain.errors import InvalidZipCode
from pawdesk.shared.constants.regex import NON_DIGITS_RE


@dataclass(frozen=True)
class ZipCode:
    digits: str

    def __post_init__(self) -> None:
        cleaned = NON_DIGITS_RE.sub("", self.digits)
        if len(cleaned) != 8:
            raise InvalidZipCode("CEP inválido. Informe os 8 dígitos (ex.: 01310-100).")
        object.__setattr__(self, "digits", cleaned)

    @classmethod
    def parse(cls, raw: str) -> "ZipCode":
        return cls(digits=raw)

    def formatted(self) -> str:
        return f"{self.digits[:5]}-{self.digits[5:]}"


@dataclass(frozen=True)
class AddressSummary:
    city: str
    state: str
    zip_code: ZipCode
