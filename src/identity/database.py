"""
═══════════════════════════════════════════════════════════════════════════════
Identity — Пул соединений к базе данных (Database Connection Pool)
═══════════════════════════════════════════════════════════════════════════════

Собственный пул соединений к PostgreSQL для Identity-микросервиса.
Полностью аналогичен ``recon.database``, но использует собственные настройки
из ``identity.config.get_settings()``.

Создано в рамках Этапа 3, шаг 3.1 (change.md §5).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from identity.config import get_settings

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Глобальная переменная пула (module-level singleton)
# ═══════════════════════════════════════════════════════════════════════════════
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """
    Возвращает глобальный пул соединений к PostgreSQL Identity DB.

    Создаёт пул при первом вызове с параметрами из IdentitySettings.
    """
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.database_pool_min,
            max_size=settings.database_pool_max,
            command_timeout=60,
        )
        logger.info(
            f"Identity DB pool created "
            f"(min={settings.database_pool_min}, max={settings.database_pool_max})"
        )
    return _pool


async def close_pool() -> None:
    """Закрывает глобальный пул соединений Identity DB."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Identity DB pool closed")


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Выдаёт соединение из пула Identity DB и возвращает его обратно.

    Использование::

        from identity.database import get_connection

        async with get_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def check_connection() -> bool:
    """Проверяет доступность Identity PostgreSQL (health check)."""
    try:
        async with get_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error(f"Identity DB health check failed: {e}")
        return False
