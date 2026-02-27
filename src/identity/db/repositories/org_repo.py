"""
identity/db/repositories/org_repo.py — Репозиторий организаций (Identity).

Перенесено из recon/db/repositories/org_repo.py в рамках Этапа 2 (шаг 2.2).
Разделение выполнено на Этапе 3, шаг 3.1.

References:
    - [change.md: Этап 2, шаг 2.2]
    - [change.md: Этап 3, шаг 3.1]
"""

from __future__ import annotations

from uuid import UUID

from identity.database import get_connection


async def create_organization(
    name: str,
    inn: str,
    ogrn: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> dict:
    """Создать новую организацию."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO organizations (name, inn, ogrn, email, phone)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING org_id, name, inn, ogrn, email, phone
            """,
            name, inn, ogrn, email, phone,
        )
        return dict(row) if row else {}


async def link_user_to_org(org_id: UUID, user_id: UUID, role: str = "accountant") -> None:
    """Привязать пользователя к организации."""
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO org_users (org_id, user_id, role, status)
            VALUES ($1, $2, $3, 'pending')
            ON CONFLICT (org_id, user_id) DO NOTHING
            """,
            org_id, user_id, role,
        )


async def get_orgs_for_user(user_id: UUID) -> list[dict]:
    """Получить все организации пользователя."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT o.* FROM organizations o
            JOIN org_users ou ON o.org_id = ou.org_id
            WHERE ou.user_id = $1
            ORDER BY o.name
            """,
            user_id,
        )
        return [dict(r) for r in rows]


async def get_org_by_id(org_id: UUID) -> dict | None:
    """Найти организацию по UUID."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM organizations WHERE org_id = $1", org_id
        )
        return dict(row) if row else None


async def get_linked_users(org_id: UUID) -> list[dict]:
    """Получить пользователей организации."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT ou.user_id, ou.role, ou.status
            FROM org_users ou
            WHERE ou.org_id = $1
            """,
            org_id,
        )
        return [dict(r) for r in rows]
