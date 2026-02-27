"""
identity/services/org_service.py — Сервис управления организациями (Identity).

Перенесено из recon/services/org_service.py в рамках Этапа 2 (шаг 2.2).
Все импорты переключены на identity.* (exceptions, модели, репозитории).
Полностью независим от recon.* (Этап 3, шаг 3.1).

References:
    - [change.md: Этап 2, шаг 2.2]
    - [RECON TZ: Section 2.2] Управление организациями
"""

from __future__ import annotations

import logging
from uuid import UUID

# Identity-собственная инфраструктура (Этап 3, шаг 3.1)
from identity.exceptions import AuthorizationError, ConflictError, NotFoundError

# Identity-домен: собственные модули
from identity.adapters.egrul_client import lookup_by_inn
from identity.db.repositories import org_repo, user_repo
from identity.models.organization import LinkedUser, OrganizationCreate, OrganizationRead

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# МАППИНГ БД-СТРОКИ → Pydantic-МОДЕЛЬ
# ═══════════════════════════════════════════════════════════════════════════


def _org_row_to_read(row: dict, linked_users: list[dict] | None = None) -> OrganizationRead:
    """Конвертирует строку из БД (dict) → OrganizationRead."""
    users = []
    if linked_users:
        users = [
            LinkedUser(
                user_id=u["user_id"],
                role=u.get("role", "accountant"),
                status=u.get("status", "pending"),
            )
            for u in linked_users
        ]
    return OrganizationRead(
        org_id=row["org_id"],
        name=row["name"],
        inn=row["inn"],
        ogrn=row.get("ogrn"),
        email=row.get("email"),
        phone=row.get("phone"),
        linked_users=users,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CRUD-ОПЕРАЦИИ
# ═══════════════════════════════════════════════════════════════════════════


async def create_organization(data: OrganizationCreate, user_id: UUID) -> OrganizationRead:
    """Создаёт организацию и привязывает текущего пользователя как директора."""
    egrul_data = await lookup_by_inn(data.inn)
    name = data.name
    ogrn = data.ogrn
    if egrul_data:
        name = egrul_data.get("name", name)
        ogrn = egrul_data.get("ogrn", ogrn)
        logger.info("Enriched org data from EGRUL for INN %s", data.inn)

    row = await org_repo.create_organization(
        name=name,
        inn=data.inn,
        ogrn=ogrn,
        email=data.email,
        phone=data.phone,
    )

    await org_repo.link_user_to_org(row["org_id"], user_id, role="director")

    # NATS event (Этап 3, шаг 3.5) — graceful degradation
    try:
        from identity.events import emit_org_created
        await emit_org_created(
            org_id=str(row["org_id"]),
            inn=data.inn,
            name=name,
        )
    except Exception as exc:
        logger.warning("Failed to emit org.created event: %s", exc)

    linked = await org_repo.get_linked_users(row["org_id"])
    return _org_row_to_read(row, linked)


async def get_user_organizations(user_id: UUID) -> list[OrganizationRead]:
    """Возвращает все организации, к которым привязан пользователь."""
    rows = await org_repo.get_orgs_for_user(user_id)
    result = []
    for r in rows:
        linked = await org_repo.get_linked_users(r["org_id"])
        result.append(_org_row_to_read(r, linked))
    return result


async def get_organization(org_id: UUID, user_id: UUID) -> OrganizationRead:
    """Возвращает организацию, если пользователь к ней привязан."""
    row = await org_repo.get_org_by_id(org_id)
    if not row:
        raise NotFoundError("Organization", str(org_id))

    linked = await org_repo.get_linked_users(org_id)
    user_ids = {u["user_id"] for u in linked}
    if user_id not in user_ids:
        raise NotFoundError("Organization", str(org_id))

    return _org_row_to_read(row, linked)


async def invite_user_to_org(
    org_id: UUID, inviter_id: UUID, target_inn: str, role: str
) -> None:
    """Приглашает ФЛ-пользователя в организацию по ИНН."""
    org = await org_repo.get_org_by_id(org_id)
    if not org:
        raise NotFoundError("Organization", str(org_id))

    linked = await org_repo.get_linked_users(org_id)
    inviter_roles = [u for u in linked if u["user_id"] == inviter_id]
    if not inviter_roles or inviter_roles[0].get("role") != "director":
        raise AuthorizationError("Only a director can invite users to an organization")

    target_user = await user_repo.get_user_by_inn(target_inn)
    if not target_user:
        raise NotFoundError("User", f"INN={target_inn}")

    await org_repo.link_user_to_org(org_id, target_user["user_id"], role=role)
    logger.info(
        "User %s invited user INN=%s to org %s with role %s",
        inviter_id, target_inn, org_id, role,
    )
