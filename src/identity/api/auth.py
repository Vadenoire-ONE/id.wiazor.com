"""
identity/api/auth.py — Эндпоинты аутентификации (Identity-пакет).

Перенесено из recon/api/v1/auth.py в рамках Этапа 2 (шаг 2.2).
Все импорты переключены на identity.* (Этап 3, шаг 3.1).

References:
    - [change.md: Этап 2, шаг 2.2]
    - [RECON TZ: Section 5.1] /signup/* endpoints
"""

from fastapi import APIRouter, Body, status

from identity.models.user import UserCreate, UserRead
from identity.services import auth_service

router = APIRouter(tags=["auth"])


@router.post(
    "/signup/start",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Начало регистрации ФЛ-пользователя",
)
async def signup_start(body: UserCreate):
    """Шаг 1 — Регистрация нового ФЛ-пользователя."""
    return await auth_service.register_user(body)


@router.post(
    "/signup/confirm-email",
    status_code=status.HTTP_200_OK,
    summary="Подтверждение email по коду",
)
async def confirm_email(email: str = Body(...), code: str = Body(...)):
    """Шаг 2 — Подтверждение email одноразовым 6-значным кодом."""
    result = await auth_service.confirm_email(email, code)
    return {"confirmed": result}


@router.post(
    "/login",
    summary="Вход по email + пароль → JWT-токен",
)
async def login(email: str = Body(...), password: str = Body(...)):
    """Аутентификация: email + пароль → JWT access + refresh."""
    return await auth_service.authenticate(email, password)


@router.post(
    "/token/refresh",
    summary="Обновить JWT-токен",
)
async def refresh_token(refresh_token: str = Body(..., alias="refresh_token")):
    """Выдать новый access_token по refresh_token."""
    return await auth_service.refresh_access_token(refresh_token)
