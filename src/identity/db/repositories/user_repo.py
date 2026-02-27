"""
identity/db/repositories/user_repo.py — Репозиторий пользователей (Identity).

Перенесено из recon/db/repositories/user_repo.py в рамках Этапа 2 (шаг 2.2).
Использует собственную инфраструктуру БД (identity.database).
Разделение выполнено на Этапе 3, шаг 3.1.

References:
    - [change.md: Этап 2, шаг 2.2]
    - [change.md: Этап 3, шаг 3.1]
"""

from __future__ import annotations

from uuid import UUID

from identity.database import get_connection


async def create_user(
    full_name: str,
    inn: str,
    email: str,
    phone: str,
    password_hash: str,
) -> dict:
    """Создать нового пользователя."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (full_name, inn, email, phone, password_hash)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING user_id, full_name, inn, email, phone, status, created_at
            """,
            full_name, inn, email, phone, password_hash,
        )
        return dict(row) if row else {}


async def get_user_by_id(user_id: UUID) -> dict | None:
    """Найти пользователя по UUID."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE user_id = $1", user_id
        )
        return dict(row) if row else None


async def get_user_by_email(email: str) -> dict | None:
    """Найти пользователя по email."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1", email
        )
        return dict(row) if row else None


async def get_user_by_inn(inn: str) -> dict | None:
    """Найти пользователя по ИНН."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE inn = $1", inn
        )
        return dict(row) if row else None


async def update_user_status(user_id: UUID, status: str) -> None:
    """Обновить статус пользователя."""
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE users SET status = $1, updated_at = NOW() WHERE user_id = $2",
            status, user_id,
        )
