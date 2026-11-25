"""Utilitários de data e dias úteis (sem relógio global)."""

from datetime import datetime, timedelta

from pawdesk.shared.constants.locale import (
    BUSINESS_HOURS_END,
    BUSINESS_HOURS_START,
    BUSINESS_WEEKDAYS,
    DEFAULT_TIMEZONE,
)


def to_local(dt: datetime) -> datetime:
    """Converte um datetime para o fuso padrão America/Sao_Paulo."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=DEFAULT_TIMEZONE)
    return dt.astimezone(DEFAULT_TIMEZONE)


def add_business_days(start: datetime, days: int) -> datetime:
    """Soma dias úteis (segunda a sexta) preservando o horário local."""
    if days < 0:
        raise ValueError("days deve ser >= 0.")
    current = to_local(start)
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() in BUSINESS_WEEKDAYS:
            added += 1
    return current


def business_days_between(start: datetime, end: datetime) -> int:
    """Conta quantos dias úteis completos se passaram entre `start` e `end`."""
    start_date = to_local(start).date()
    end_date = to_local(end).date()
    if end_date <= start_date:
        return 0
    count = 0
    cursor = start_date + timedelta(days=1)
    while cursor <= end_date:
        if cursor.weekday() in BUSINESS_WEEKDAYS:
            count += 1
        cursor += timedelta(days=1)
    return count


def is_business_hours(now: datetime) -> bool:
    """Indica se o instante fornecido está dentro do horário comercial padrão."""
    local_dt = to_local(now)
    if local_dt.weekday() not in BUSINESS_WEEKDAYS:
        return False
    current_time = local_dt.timetz().replace(tzinfo=None)
    return BUSINESS_HOURS_START <= current_time < BUSINESS_HOURS_END
