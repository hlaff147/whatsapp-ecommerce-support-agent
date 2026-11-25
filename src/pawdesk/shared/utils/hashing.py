"""Hashing seguro, comparação em tempo constante e pseudonimização."""

import hashlib
import hmac


def hmac_sha256(value: str | bytes, secret: str | bytes) -> str:
    """Calcula HMAC-SHA256 hexadecimal."""
    secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret
    value_bytes = value.encode("utf-8") if isinstance(value, str) else value
    return hmac.new(secret_bytes, value_bytes, hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    """Compara strings em tempo constante para mitigar timing attacks."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def pseudonymize(value: str, secret: str) -> str:
    """Gera identificador estável de 24 caracteres não reversível (ex.: user_id ADK)."""
    return hmac_sha256(value, secret)[:24]
