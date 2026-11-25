"""Testes unitários dos utilitários puros em pawdesk.shared."""

from datetime import UTC, datetime

import pytest

from pawdesk.shared.utils.cpf import is_valid_cpf, last_digits, mask_cpf
from pawdesk.shared.utils.dates import (
    add_business_days,
    business_days_between,
    is_business_hours,
)
from pawdesk.shared.utils.hashing import constant_time_equals, pseudonymize
from pawdesk.shared.utils.ids import new_ulid
from pawdesk.shared.utils.masking import mask_email, mask_phone, redact_pii
from pawdesk.shared.utils.phone import is_valid_br_mobile, to_e164
from pawdesk.shared.utils.text import split_for_whatsapp, truncate_for_whatsapp


def test_phone_e164_and_validation() -> None:
    assert to_e164("(11) 99999-0001") == "+5511999990001"
    assert to_e164("+55 11 99999-0001") == "+5511999990001"
    assert is_valid_br_mobile("11999990001") is True
    assert is_valid_br_mobile("1133330001") is False
    with pytest.raises(ValueError):
        to_e164("123")


def test_cpf_utils() -> None:
    assert is_valid_cpf("52998224725") is True
    assert is_valid_cpf("11111111111") is False
    assert is_valid_cpf("52998224726") is False
    assert last_digits("529.982.247-25", 3) == "725"
    assert mask_cpf("52998224725") == "***.***.*7-25"


def test_masking_and_redact_pii() -> None:
    assert mask_email("marina.silva@example.com") == "ma***@example.com"
    assert mask_phone("+5511999990001") == "***0001"
    raw = "Meu CPF é 529.982.247-25, email marina@pet.com e tel (11) 99999-0001."
    redacted = redact_pii(raw)
    assert "529" not in redacted
    assert "marina@pet.com" not in redacted
    assert "99999-0001" not in redacted
    assert "[EMAIL]" in redacted
    assert "[TELEFONE]" in redacted


def test_dates_business_days_and_hours() -> None:
    # Sexta-feira 14:00 UTC = 11:00 BRT
    friday = datetime(2026, 11, 20, 14, 0, tzinfo=UTC)
    assert is_business_hours(friday) is True
    # +1 dia útil pula sábado e domingo -> segunda 23/11
    monday = add_business_days(friday, 1)
    assert monday.date().isoformat() == "2026-11-23"
    assert business_days_between(friday, monday) == 1

    # Sábado não é horário comercial
    saturday = datetime(2026, 11, 21, 15, 0, tzinfo=UTC)
    assert is_business_hours(saturday) is False
    # Terça 22:00 BRT (01:00 UTC do dia seguinte) não é horário comercial
    night_brt = datetime(2026, 11, 25, 1, 0, tzinfo=UTC)
    assert is_business_hours(night_brt) is False


def test_ids_hashing_and_text() -> None:
    u1 = new_ulid()
    u2 = new_ulid()
    assert len(u1) == 26
    assert u1 != u2

    p1 = pseudonymize("+5511999990001", "secret")
    p2 = pseudonymize("+5511999990001", "secret")
    assert len(p1) == 24
    assert p1 == p2
    assert constant_time_equals("abc", "abc") is True
    assert constant_time_equals("abc", "abd") is False

    assert truncate_for_whatsapp("abcdef", max_chars=5) == "ab..."
    assert split_for_whatsapp("uma frase longa aqui", max_chars=10) == [
        "uma frase",
        "longa aqui",
    ]
