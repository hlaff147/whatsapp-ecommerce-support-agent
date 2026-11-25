"""Cifra simétrica para proteção de telefone em repouso (LGPD)."""

import base64
import hashlib

from cryptography.fernet import Fernet


def _normalize_fernet_key(raw_key: str) -> bytes:
    """Garante chave Fernet válida de 32 bytes base64 a partir da configuração."""
    candidate = raw_key.encode("utf-8")
    try:
        Fernet(candidate)
        return candidate
    except Exception:
        digest = hashlib.sha256(candidate).digest()
        return base64.urlsafe_b64encode(digest)


class FernetSecretCipher:
    """Implementa SecretCipher usando Fernet (AES-128-CBC + HMAC-SHA256)."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(_normalize_fernet_key(key))

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, ciphertext: bytes) -> str:
        return self._fernet.decrypt(ciphertext).decode("utf-8")
