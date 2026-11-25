"""Constantes de localização, fuso horário e horário comercial padrão."""

from datetime import time
from zoneinfo import ZoneInfo

DEFAULT_LOCALE = "pt-BR"
DEFAULT_TIMEZONE_NAME = "America/Sao_Paulo"
DEFAULT_TIMEZONE = ZoneInfo(DEFAULT_TIMEZONE_NAME)

BUSINESS_HOURS_START = time(9, 0)
BUSINESS_HOURS_END = time(18, 0)
# Segunda (0) a Sexta (4)
BUSINESS_WEEKDAYS = frozenset({0, 1, 2, 3, 4})
