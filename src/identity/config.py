"""
═══════════════════════════════════════════════════════════════════════════════
Identity — Настройки микросервиса (Application Configuration)
═══════════════════════════════════════════════════════════════════════════════

Собственный класс IdentitySettings для независимого Identity-сервиса.
Содержит настройки:
    • Database (PostgreSQL — отдельная БД identity_db)
    • API server (host, port)
    • JWT / аутентификация
    • CORS
    • Rate Limiting
    • NATS (для публикации событий)

Создано в рамках Этапа 3, шаг 3.1 (change.md §5).
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class IdentitySettings(BaseSettings):
    """
    Настройки Identity-микросервиса.

    Все параметры читаются из переменных окружения или .env файла.
    Префикс не используется — переменные совпадают с RECON для
    бесшовного перехода (JWT_SECRET_KEY, DATABASE_URL и т.д.).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Среда выполнения ──────────────────────────────────────────────────
    app_env: str = Field(
        default="development",
        description="Application environment: development | staging | production",
    )

    # ── Database (Identity-собственная БД) ────────────────────────────────
    database_url: str = Field(
        default="postgresql://identity_user:changeme@localhost:5433/identity_db",
        description="PostgreSQL connection string for Identity database",
    )
    database_pool_min: int = Field(default=2, ge=1)
    database_pool_max: int = Field(default=10, ge=2)

    # ── API server ────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8200, ge=1, le=65535)
    log_level: str = Field(default="INFO")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | List[str]) -> List[str]:
        """Парсит CORS_ORIGINS из JSON-строки."""
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ── JWT ───────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(default="CHANGE_ME_IN_PRODUCTION")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)

    # ── Asymmetric JWT (Step 3.4) ─────────────────────────────────────────
    # Когда jwt_private_key_path задан, Identity подписывает JWT приватным
    # ключом (RS256/ES256). Публичный ключ выставляется через JWKS endpoint.
    jwt_private_key_path: str = Field(
        default="",
        description="Path to RSA/EC private key PEM file for JWT signing",
    )
    jwt_public_key_path: str = Field(
        default="",
        description="Path to RSA/EC public key PEM file (served via JWKS)",
    )

    # ── NATS (публикация событий) ─────────────────────────────────────────
    nats_url: str = Field(default="nats://localhost:4222")

    # ── Rate Limiting ─────────────────────────────────────────────────────
    rate_limit_auth_rpm: int = Field(
        default=20,
        description="Max requests per minute to auth endpoints (login/signup)",
    )
    rate_limit_api_rpm: int = Field(
        default=300,
        description="Max requests per minute to general API endpoints",
    )

    # ── Валидация JWT-секрета (P0 security) ───────────────────────────────
    @model_validator(mode="after")
    def _validate_jwt_secret(self) -> "IdentitySettings":
        """
        В production обязательно заменить JWT_SECRET_KEY!

        Исключение: если используется asymmetric JWT (jwt_private_key_path задан),
        shared secret не требуется для подписи (хотя рекомендуется для fallback).
        """
        unsafe = {"CHANGE_ME_IN_PRODUCTION", "secret", "changeme", ""}
        if self.app_env == "production" and self.jwt_secret_key in unsafe:
            if not self.jwt_private_key_path:
                raise ValueError(
                    "P0 SECURITY: JWT_SECRET_KEY must be changed for production! "
                    "Or configure JWT_PRIVATE_KEY_PATH for asymmetric JWT. "
                    'Generate HS256 secret: python -c "import secrets; print(secrets.token_hex(32))"'
                )
        return self


@lru_cache
def get_settings() -> IdentitySettings:
    """
    Возвращает единственный экземпляр IdentitySettings (singleton).

    Декоратор ``@lru_cache`` гарантирует, что объект создаётся
    только при первом вызове.
    """
    return IdentitySettings()


__all__ = ["IdentitySettings", "get_settings"]
