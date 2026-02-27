"""
identity/api/health.py — Health check эндпоинт Identity-сервиса.

GET /api/v1/health — проверяет доступность Identity PostgreSQL.

Создано в рамках Этапа 3, шаг 3.1 (change.md §5).
"""

from fastapi import APIRouter

from identity.database import check_connection

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check Identity-сервиса")
async def health():
    """Проверяет доступность Identity DB."""
    db_ok = await check_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "service": "identity",
    }
