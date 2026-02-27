"""
identity/api/internal.py — Внутренние эндпоинты для inter-service communication.

Используются RemoteIdentityGateway из RECON-сервиса для получения
данных о пользователях и организациях.

Создано в рамках Этапа 3, шаг 3.1 + 3.3 (change.md §5).
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from identity.db.repositories import user_repo, org_repo

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get(
    "/users/{user_id}",
    summary="[Internal] Получить пользователя по UUID",
)
async def get_user(user_id: UUID):
    """Внутренний эндпоинт для RemoteIdentityGateway."""
    user = await user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Не возвращаем password_hash
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    return safe


@router.get(
    "/users/{user_id}/orgs",
    summary="[Internal] Получить организации пользователя",
)
async def get_user_orgs(user_id: UUID):
    """Внутренний эндпоинт: список организаций пользователя."""
    orgs = await org_repo.get_orgs_for_user(user_id)
    return orgs


@router.get(
    "/orgs/{org_id}",
    summary="[Internal] Получить организацию по UUID",
)
async def get_org(org_id: UUID):
    """Внутренний эндпоинт: данные организации."""
    org = await org_repo.get_org_by_id(org_id)
    return org


@router.get(
    "/orgs/{org_id}/users",
    summary="[Internal] Получить пользователей организации",
)
async def get_org_users(org_id: UUID):
    """Внутренний эндпоинт: список пользователей организации."""
    users = await org_repo.get_linked_users(org_id)
    return users
