"""
identity/services/auth_service.py — Сервис аутентификации (Identity).

Перенесено из recon/services/auth_service.py в рамках Этапа 2 (шаг 2.2).
Все импорты переключены на identity.* (config, exceptions, модели, репозитории).
Полностью независим от recon.* (Этап 3, шаг 3.1).

References:
    - [change.md: Этап 2, шаг 2.2]
    - [RECON TZ: Section 2.1] Регистрация ФЛ-пользователя
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from jose import jwt
import bcrypt

# Identity-собственная инфраструктура (Этап 3, шаг 3.1)
from identity.config import get_settings
from identity.exceptions import AuthenticationError, ConflictError, ValidationError

# Identity-домен: собственные модули
from identity.db.repositories import user_repo
from identity.db.repositories import org_repo
from identity.models.user import UserCreate, UserRead

logger = logging.getLogger(__name__)

settings = get_settings()

_email_codes: dict[str, str] = {}


# ═══════════════════════════════════════════════════════════════════════════
# ЗАГРУЗКА КЛЮЧЕЙ (Шаг 3.4 — Asymmetric JWT)
# ═══════════════════════════════════════════════════════════════════════════

_private_key_cache: str | None = None
_public_key_cache: str | None = None


def _get_jwt_signing_key() -> str:
    """
    Возвращает ключ подписи JWT.

    Приоритет:
    1. RSA/EC private key (из файла jwt_private_key_path) → RS256/ES256
    2. Shared secret (jwt_secret_key) → HS256 (fallback)
    """
    global _private_key_cache
    if settings.jwt_private_key_path:
        if _private_key_cache is None:
            from pathlib import Path
            p = Path(settings.jwt_private_key_path)
            if p.is_file():
                _private_key_cache = p.read_text(encoding="utf-8")
                logger.info("JWT signing: RSA/EC private key loaded from %s", p)
            else:
                logger.warning("JWT private key file not found: %s, falling back to HS256", p)
                return settings.jwt_secret_key
        return _private_key_cache
    return settings.jwt_secret_key


def _get_jwt_algorithm() -> str:
    """Определяет алгоритм JWT на основе конфигурации."""
    if settings.jwt_private_key_path:
        return "RS256"
    return settings.jwt_algorithm


def _get_jwt_public_key() -> str | None:
    """Возвращает публичный ключ для верификации JWT (если настроен)."""
    global _public_key_cache
    if settings.jwt_public_key_path:
        if _public_key_cache is None:
            from pathlib import Path
            p = Path(settings.jwt_public_key_path)
            if p.is_file():
                _public_key_cache = p.read_text(encoding="utf-8")
        return _public_key_cache
    return None


def _get_jwt_verify_key() -> str:
    """Ключ для верификации JWT (public key или shared secret)."""
    pub = _get_jwt_public_key()
    return pub if pub else settings.jwt_secret_key


# ═══════════════════════════════════════════════════════════════════════════
# РАБОТА С ПАРОЛЯМИ
# ═══════════════════════════════════════════════════════════════════════════


def hash_password(password: str) -> str:
    """Хеширует пароль с помощью bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Сравнивает открытый пароль с хешем из БД."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ═══════════════════════════════════════════════════════════════════════════
# JWT-ТОКЕНЫ
# ═══════════════════════════════════════════════════════════════════════════


def create_access_token(
    user_id: UUID,
    expires_delta: timedelta | None = None,
    role: str = "viewer",
    org_ids: list[str] | None = None,
) -> str:
    """Создаёт подписанный JWT access-токен (HS256 или RS256)."""
    exp = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload: dict = {"sub": str(user_id), "exp": exp, "type": "access", "role": role}
    if org_ids is not None and len(org_ids) <= 20:
        payload["org_ids"] = org_ids
    return jwt.encode(payload, _get_jwt_signing_key(), algorithm=_get_jwt_algorithm())


def create_refresh_token(user_id: UUID) -> str:
    """Создаёт JWT refresh-токен (срок жизни 7 дней)."""
    exp = datetime.utcnow() + timedelta(days=7)
    payload = {"sub": str(user_id), "exp": exp, "type": "refresh"}
    return jwt.encode(payload, _get_jwt_signing_key(), algorithm=_get_jwt_algorithm())


def decode_token(token: str) -> dict:
    """Декодирует и проверяет JWT-токен (поддержка HS256 и RS256)."""
    algo = _get_jwt_algorithm()
    key = _get_jwt_verify_key()
    try:
        return jwt.decode(token, key, algorithms=[algo])
    except Exception as exc:
        raise AuthenticationError(f"Invalid token: {exc}") from exc


def generate_email_code() -> str:
    """Генерирует 6-значный код подтверждения email."""
    return f"{secrets.randbelow(10**6):06d}"


# ═══════════════════════════════════════════════════════════════════════════
# РЕГИСТРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════


async def register_user(data: UserCreate) -> UserRead:
    """Регистрирует нового ФЛ-пользователя."""
    existing_email = await user_repo.get_user_by_email(data.email)
    if existing_email:
        raise ConflictError(
            f"User with email '{data.email}' already exists",
            details={"field": "email"},
        )

    existing_inn = await user_repo.get_user_by_inn(data.inn)
    if existing_inn:
        raise ConflictError(
            f"User with INN '{data.inn}' already exists",
            details={"field": "inn"},
        )

    hashed = hash_password(data.password)
    row = await user_repo.create_user(
        full_name=data.full_name,
        inn=data.inn,
        email=data.email,
        phone=data.phone,
        password_hash=hashed,
    )

    code = generate_email_code()
    _email_codes[data.email] = code
    logger.info("Email confirmation code for %s: %s (dev only)", data.email, code)

    # NATS event (Этап 3, шаг 3.5) — graceful degradation if NATS unavailable
    try:
        from identity.events import emit_user_registered
        await emit_user_registered(
            user_id=str(row["user_id"]),
            email=data.email,
            inn=data.inn,
        )
    except Exception as exc:
        logger.warning("Failed to emit user.registered event: %s", exc)

    return UserRead(
        user_id=row["user_id"],
        full_name=row["full_name"],
        inn=row["inn"],
        email=row["email"],
        phone=data.phone,
        status=row.get("status", "pending"),
        created_at=row.get("created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# ПОДТВЕРЖДЕНИЕ EMAIL
# ═══════════════════════════════════════════════════════════════════════════


async def confirm_email(email: str, code: str) -> bool:
    """Подтверждает email пользователя по 6-значному коду."""
    stored_code = _email_codes.get(email)
    if not stored_code or stored_code != code:
        raise AuthenticationError("Invalid or expired confirmation code")

    user = await user_repo.get_user_by_email(email)
    if not user:
        raise AuthenticationError("User not found")

    await user_repo.update_user_status(user["user_id"], "verified")
    del _email_codes[email]
    logger.info("Email confirmed for user %s", user["user_id"])
    return True


# ═══════════════════════════════════════════════════════════════════════════
# АУТЕНТИФИКАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════


async def authenticate(email: str, password: str) -> dict:
    """Аутентифицирует пользователя (email + пароль) → JWT-токены."""
    user = await user_repo.get_user_by_email(email)
    if not user:
        raise AuthenticationError("Invalid email or password")

    if not verify_password(password, user["password_hash"]):
        raise AuthenticationError("Invalid email or password")

    if user.get("status") == "blocked":
        raise AuthenticationError("Account is blocked")

    user_id = user["user_id"]
    user_role = user.get("role", "viewer")
    orgs = await org_repo.get_orgs_for_user(user_id)
    org_ids = [str(o["org_id"]) for o in orgs]
    access = create_access_token(user_id, role=user_role, org_ids=org_ids)
    refresh = create_refresh_token(user_id)

    user_read = UserRead(
        user_id=user_id,
        full_name=user["full_name"],
        inn=user["inn"],
        email=user["email"],
        phone=user.get("phone", ""),
        status=user.get("status", "pending"),
        created_at=user.get("created_at"),
    )

    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": user_read,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ОБНОВЛЕНИЕ ТОКЕНА
# ═══════════════════════════════════════════════════════════════════════════


async def refresh_access_token(refresh_token_str: str) -> dict:
    """Выдаёт новую пару токенов по валидному refresh-токену."""
    payload = decode_token(refresh_token_str)
    if payload.get("type") != "refresh":
        raise AuthenticationError("Token is not a refresh token")

    user_id = UUID(payload["sub"])
    user = await user_repo.get_user_by_id(user_id)
    if not user:
        raise AuthenticationError("User not found")

    user_role = user.get("role", "viewer")
    orgs = await org_repo.get_orgs_for_user(user_id)
    org_ids = [str(o["org_id"]) for o in orgs]
    new_access = create_access_token(user_id, role=user_role, org_ids=org_ids)
    new_refresh = create_refresh_token(user_id)
    return {"access_token": new_access, "refresh_token": new_refresh}
