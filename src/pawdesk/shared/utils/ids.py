"""Geração de identificadores ordenáveis (ULID de 26 caracteres) e correlation IDs."""

import os
import time
import uuid

_CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_crockford(value: int, length: int) -> str:
    chars = ["0"] * length
    for idx in range(length - 1, -1, -1):
        chars[idx] = _CROCKFORD_ALPHABET[value & 0x1F]
        value >>= 5
    return "".join(chars)


def new_ulid() -> str:
    """Gera um ULID de 26 caracteres (stdlib pura, ordenável lexicograficamente)."""
    timestamp_ms = time.time_ns() // 1_000_000
    randomness = int.from_bytes(os.urandom(10), "big")
    return _encode_crockford(timestamp_ms, 10) + _encode_crockford(randomness, 16)


def new_correlation_id() -> str:
    """Gera um identificador único de correlação para rastreabilidade."""
    return uuid.uuid4().hex
