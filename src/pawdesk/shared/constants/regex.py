"""Expressões regulares compiladas para validação e mascaramento."""

import re

CPF_RE = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)9?\d{4}-?\d{4}")
ZIP_CODE_RE = re.compile(r"^\d{5}-?\d{3}$")
ORDER_NUMBER_RE = re.compile(r"\bPD[- ]?(\d{5,8})\b", re.IGNORECASE)
NON_DIGITS_RE = re.compile(r"\D+")
WHITESPACE_RE = re.compile(r"\s+")
