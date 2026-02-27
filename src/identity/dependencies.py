"""
═══════════════════════════════════════════════════════════════════════════════
Identity — Зависимости FastAPI (Dependency Injection)
═══════════════════════════════════════════════════════════════════════════════

Собственная реализация ``get_current_user()`` для Identity-микросервиса.
Не зависит от recon.* — использует только identity.* модули.

Создано в рамках Этапа 3, шаг 3.1 (change.md §5).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Header, HTTPException, status

from identity.db.repositories import user_repo
from identity.models.user import UserRead
from identity.services.auth_service import decode_token


async def get_current_user(authorization: str | None = Header(None)) -> UserRead:
    """
    Извлекает и валидирует JWT-токен из заголовка ``Authorization``.

    Алгоритм:
        1. Проверяет наличие и формат заголовка Authorization.
        2. Декодирует JWT (подпись + срок действия).
        3. Загружает пользователя из Identity DB по UUID (claim ``sub``).
        4. Проверяет статус ``blocked``.
        5. Возвращает UserRead.

    Returns:
        UserRead с данными аутентифицированного пользователя.

    Raises:
        HTTPException(401): токен отсутствует, невалиден, пользователь не найден.
        HTTPException(403): учётная запись заблокирована.
    """
    # ── Шаг 1: наличие заголовка ──
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Шаг 2: формат "Bearer <token>" ──
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must start with 'Bearer'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]
    try:
        # ── Шаг 3: декодирование JWT ──
        payload = decode_token(token)

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing 'sub'",
            )

        jwt_role = payload.get("role")

        # ── Шаг 4: загрузка пользователя из Identity DB ──
        user = await user_repo.get_user_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # ── Шаг 5: проверка блокировки ──
        if user.get("status") == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is blocked",
            )

        # ── Шаг 6: формирование UserRead ──
        effective_role = jwt_role or user.get("role", "viewer")
        return UserRead(
            user_id=user["user_id"],
            full_name=user["full_name"],
            inn=user["inn"],
            email=user["email"],
            phone=user.get("phone", ""),
            status=user.get("status", "pending"),
            role=effective_role,
            created_at=user.get("created_at"),
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
