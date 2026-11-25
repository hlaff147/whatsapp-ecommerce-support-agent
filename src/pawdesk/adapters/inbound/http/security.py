"""Verificação de assinatura HMAC do WhatsApp e autenticação de rotas internas."""

from fastapi import HTTPException

from pawdesk.shared.utils.hashing import constant_time_equals, hmac_sha256


def verify_meta_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Valida cabeçalho X-Hub-Signature-256 usando comparação em tempo constante."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac_sha256(raw_body, app_secret)
    return constant_time_equals(signature_header, expected)


def require_bearer_token(authorization: str | None, expected_token: str) -> None:
    """Exige Authorization: Bearer <token> válido para endpoints administrativos/webhook."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente.")
    provided = authorization.removeprefix("Bearer ").strip()
    if not constant_time_equals(provided, expected_token):
        raise HTTPException(status_code=403, detail="Token inválido.")
