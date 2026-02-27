"""
═══════════════════════════════════════════════════════════════════════════════
Identity.wiazor.com — Главная точка входа микросервиса (Application Entry Point)
═══════════════════════════════════════════════════════════════════════════════

Фабрика приложения (Application Factory Pattern) для Identity-микросервиса.
Паттерн идентичен ``recon.main``, но содержит только Identity-роутеры
и собственные обработчики ошибок.

Создано в рамках Этапа 3, шаг 3.1 (change.md §5).
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from identity import __version__
from identity.config import get_settings
from identity.database import close_pool, get_pool
from identity.exceptions import IdentityError

# ── Identity API роутеры ─────────────────────────────────────────────────
from identity.api.auth import router as auth_router
from identity.api.organizations import router as org_router

# ═══════════════════════════════════════════════════════════════════════════════
# Настройка логирования
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Автоматическое применение SQL-миграций
# ═══════════════════════════════════════════════════════════════════════════════

async def _apply_migrations(pool) -> None:
    """Применяет SQL-миграции из ``identity/db/migrations/``."""
    from pathlib import Path

    migrations_dir = Path(__file__).parent / "db" / "migrations"
    if not migrations_dir.is_dir():
        logger.info("No migrations directory found — skipping")
        return

    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        logger.info("No SQL migration files found — skipping")
        return

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _applied_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        rows = await conn.fetch("SELECT filename FROM _applied_migrations")
        applied = {row["filename"] for row in rows}

        for sql_file in sql_files:
            if sql_file.name in applied:
                continue

            logger.info(f"📄 Applying migration: {sql_file.name}")
            sql_text = sql_file.read_text(encoding="utf-8")
            async with conn.transaction():
                await conn.execute(sql_text)
                await conn.execute(
                    "INSERT INTO _applied_migrations (filename) VALUES ($1)",
                    sql_file.name,
                )
            logger.info(f"✅ Migration applied: {sql_file.name}")

    logger.info(f"✅ All Identity migrations up to date ({len(sql_files)} files checked)")


# ═══════════════════════════════════════════════════════════════════════════════
# Lifespan — управление жизненным циклом
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan Identity-микросервиса.

    Startup:
        1. Создаём пул соединений к Identity PostgreSQL.
        2. Применяем миграции.
        3. При недоступности БД — graceful degradation (memory store).

    Shutdown:
        1. Закрываем пул Identity DB.
    """
    settings = get_settings()
    logger.info(f"🚀 Identity.wiazor.com v{__version__} starting...")
    logger.info(f"   Log level: {settings.log_level}")

    pool = None
    try:
        pool = await get_pool()
        logger.info("✅ Identity database pool initialized")
    except Exception as e:
        logger.warning(f"⚠️  Identity DB not available — activating memory store: {e}")
        from identity.memory_store import activate_identity_memory_store
        activate_identity_memory_store()

    if pool is not None:
        try:
            await _apply_migrations(pool)
        except Exception as e:
            logger.warning(f"⚠️  Identity migration apply failed (non-fatal): {e}")

    # NATS publisher (Этап 3, шаг 3.5)
    try:
        from identity.events import connect as nats_connect
        await nats_connect()
    except Exception as e:
        logger.warning(f"⚠️  NATS publisher not available (events will be skipped): {e}")

    yield

    # Shutdown: NATS → DB
    try:
        from identity.events import disconnect as nats_disconnect
        await nats_disconnect()
    except Exception:
        pass
    try:
        await close_pool()
    except Exception:
        pass
    logger.info("🛑 Identity.wiazor.com stopped")


# ═══════════════════════════════════════════════════════════════════════════════
# Фабрика приложения
# ═══════════════════════════════════════════════════════════════════════════════

def create_app() -> FastAPI:
    """Создаёт и конфигурирует Identity FastAPI-приложение."""
    settings = get_settings()

    _is_production = settings.app_env == "production"

    app = FastAPI(
        redirect_slashes=False,
        title="Identity.wiazor.com",
        description=(
            "Identity & Authentication Service for DTKT platform. "
            "Manages user registration, authentication, JWT tokens, "
            "email verification, and organization management."
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url=None if _is_production else "/docs",
        redoc_url=None if _is_production else "/redoc",
        openapi_url=None if _is_production else "/api/v1/openapi.json",
    )

    # ── CORS middleware ──────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    )

    # ── Подключение API-роутеров ─────────────────────────────────────────
    from fastapi import APIRouter

    v1_router = APIRouter(prefix="/api/v1")
    v1_router.include_router(auth_router)
    v1_router.include_router(org_router)

    # ── Внутренние эндпоинты для inter-service communication ─────────────
    from identity.api.internal import router as internal_router
    v1_router.include_router(internal_router)

    # ── JWKS endpoint (Step 3.4 — Asymmetric JWT) ────────────────────────
    from identity.api.jwks import router as jwks_router
    v1_router.include_router(jwks_router)

    # ── Health check ─────────────────────────────────────────────────────
    from identity.api.health import router as health_router
    v1_router.include_router(health_router)

    app.include_router(v1_router)

    # ── Глобальный обработчик IdentityError ──────────────────────────────
    @app.exception_handler(IdentityError)
    async def identity_error_handler(request: Request, exc: IdentityError) -> JSONResponse:
        """Маппинг кодов Identity на HTTP-статусы."""
        status_map = {
            "IDENTITY_NOT_FOUND": 404,
            "IDENTITY_CONFLICT": 409,
            "IDENTITY_VALIDATION_ERROR": 422,
            "IDENTITY_AUTH_ERROR": 401,
            "IDENTITY_AUTHZ_ERROR": 403,
        }
        status_code = status_map.get(exc.code, 500)
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    # ── Корневой эндпоинт ────────────────────────────────────────────────
    @app.get("/")
    async def root():
        return {
            "name": "Identity.wiazor.com",
            "version": __version__,
            "description": "Identity & Authentication Service",
            "docs": "/docs",
            "api": {
                "v1": {
                    "health": "/api/v1/health",
                    "signup": "/api/v1/signup/start",
                    "login": "/api/v1/login",
                    "organizations": "/api/v1/orgs/my",
                },
            },
        }

    return app


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════════════════════════
app = create_app()


def main() -> None:
    """Запускает Identity-сервис через Uvicorn."""
    settings = get_settings()
    logger.info(f"Starting Identity server on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "identity.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
