"""
identity/api/organizations.py — Эндпоинты управления организациями (Identity-пакет).

Перенесено из recon/api/v1/organizations.py в рамках Этапа 2 (шаг 2.2).
Все импорты переключены на identity.* (Этап 3, шаг 3.1).
get_current_user импортируется из identity.dependencies.

References:
    - [change.md: Этап 2, шаг 2.2]
    - [RECON TZ: Section 5.1] /orgs/* endpoints
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from identity.dependencies import get_current_user  # Identity-собственный (Этап 3)

from identity.models.organization import OrganizationCreate, OrganizationRead
from identity.models.user import UserRead
from identity.services import org_service

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.get(
    "/my",
    response_model=list[OrganizationRead],
    summary="Список организаций текущего пользователя",
)
async def list_my_orgs(user: UserRead = Depends(get_current_user)):
    """Возвращает все организации текущего пользователя."""
    return await org_service.get_user_organizations(user.user_id)


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить организацию",
)
async def create_org(
    body: OrganizationCreate,
    user: UserRead = Depends(get_current_user),
):
    """Создаёт организацию и привязывает текущего пользователя как директора."""
    return await org_service.create_organization(body, user.user_id)


@router.get(
    "/{org_id}",
    response_model=OrganizationRead,
    summary="Получить данные организации",
)
async def get_org(org_id: UUID, user: UserRead = Depends(get_current_user)):
    """Возвращает организацию по ID, если пользователь к ней привязан."""
    return await org_service.get_organization(org_id, user.user_id)


@router.post(
    "/{org_id}/users",
    status_code=status.HTTP_201_CREATED,
    summary="Пригласить пользователя в организацию",
)
async def invite_user(
    org_id: UUID,
    user_inn: str,
    role: str = "accountant",
    user: UserRead = Depends(get_current_user),
):
    """Приглашает ФЛ-пользователя по ИНН. Только директор."""
    await org_service.invite_user_to_org(org_id, user.user_id, user_inn, role)
    return {"detail": "User invited successfully"}
