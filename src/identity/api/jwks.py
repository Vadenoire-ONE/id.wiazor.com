"""
identity/api/jwks.py — JWKS (JSON Web Key Set) endpoint.

Предоставляет публичный ключ Identity-сервиса для верификации JWT
другими микросервисами (RECON, KOLMO и т.д.) без обмена секретами.

Step 3.4: Асимметричные JWT (RSA/EC).

Спецификация: RFC 7517 (JSON Web Key)
URL: GET /api/v1/.well-known/jwks.json
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from identity.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["jwks"])


@lru_cache(maxsize=1)
def _build_jwks() -> dict:
    """
    Строит JWKS из публичного ключа, указанного в конфигурации.

    Поддерживает RSA-ключи. При необходимости можно расширить
    для EC-ключей (ES256).

    Returns:
        dict: Набор ключей в формате RFC 7517 ({"keys": [...]}).
    """
    settings = get_settings()

    if not settings.jwt_public_key_path:
        return {"keys": []}

    pub_path = Path(settings.jwt_public_key_path)
    if not pub_path.is_file():
        logger.warning("JWKS: public key file not found: %s", pub_path)
        return {"keys": []}

    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

    pem_data = pub_path.read_bytes()
    pub_key = load_pem_public_key(pem_data)

    if not hasattr(pub_key, "public_numbers"):
        logger.warning("JWKS: unsupported key type (expected RSA)")
        return {"keys": []}

    numbers: RSAPublicNumbers = pub_key.public_numbers()

    import base64

    def _int_to_base64url(n: int) -> str:
        """Encode integer as Base64url (RFC 7518 §6.3)."""
        byte_length = (n.bit_length() + 7) // 8
        b = n.to_bytes(byte_length, byteorder="big")
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": "identity-1",
        "n": _int_to_base64url(numbers.n),
        "e": _int_to_base64url(numbers.e),
    }

    logger.info("JWKS: RSA public key loaded (kid=%s)", jwk["kid"])
    return {"keys": [jwk]}


@router.get(
    "/.well-known/jwks.json",
    summary="JWKS — публичные ключи Identity для JWT-верификации",
    response_class=JSONResponse,
)
async def get_jwks():
    """
    Возвращает набор публичных ключей (JWKS) Identity-сервиса.

    Другие микросервисы используют этот endpoint для верификации JWT:
    1. RECON при получении запроса скачивает JWKS (с кешированием).
    2. Извлекает публичный ключ по ``kid``.
    3. Верифицирует подпись JWT без знания приватного секрета.

    Если asymmetric JWT не настроен — возвращает пустой набор ``{"keys": []}``.
    """
    jwks = _build_jwks()
    if not jwks["keys"]:
        logger.debug("JWKS requested but no asymmetric keys configured")
    return JSONResponse(
        content=jwks,
        headers={
            "Cache-Control": "public, max-age=3600",  # Кеш 1 час
            "Content-Type": "application/json",
        },
    )
