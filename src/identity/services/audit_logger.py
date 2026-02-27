"""
identity/services/audit_logger.py — Аудит-лог Identity-домена.

Содержит Identity-специфичные AuditAction и AuditLogger.
Расщеплено из recon/services/audit_logger.py (TD-1, change.md §10.2).

Действия домена Identity:
    • user.register, user.login, user.logout, user.blocked
    • org.create, org.update, org.link_user, org.unlink_user

В монолитном режиме: пишет в общую таблицу audit_log (recon DB).
В микросервисном режиме: пишет в identity_db.audit_log + NATS-события.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class IdentityAuditAction(str, Enum):
    """Типы аудируемых действий домена Identity."""

    # Auth
    USER_REGISTER = "user.register"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_BLOCKED = "user.blocked"

    # Organizations
    ORG_CREATE = "org.create"
    ORG_UPDATE = "org.update"
    ORG_LINK_USER = "org.link_user"
    ORG_UNLINK_USER = "org.unlink_user"


class IdentityAuditLogger:
    """
    Аудит-логгер для Identity-микросервиса.

    Поддерживает:
    - PostgreSQL (identity_db.audit_log)
    - In-memory буфер (fallback)
    - NATS-публикацию аудит-событий (для RECON-подписки)
    """

    def __init__(self, max_buffer_size: int = 10000) -> None:
        self._buffer: list[dict[str, Any]] = []
        self._max_buffer = max_buffer_size

    async def log(
        self,
        action: IdentityAuditAction | str,
        entity_type: str,
        entity_id: str,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Записать аудит-событие Identity."""
        action_str = action.value if isinstance(action, IdentityAuditAction) else action
        record = {
            "action": action_str,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "details": details or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self._write_to_db(record)
        except Exception as e:
            logger.warning("Identity audit DB write failed, buffering: %s", e)
            self._write_to_buffer(record)

        # NATS-публикация (graceful degradation)
        try:
            await self._publish_nats(record)
        except Exception as e:
            logger.debug("Identity audit NATS publish failed: %s", e)

    async def _write_to_db(self, record: dict[str, Any]) -> None:
        """Записать в PostgreSQL (identity_db)."""
        import json
        from identity.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log (action, entity_type, entity_id, user_id, details)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                """,
                record["action"],
                record["entity_type"],
                record["entity_id"],
                record["user_id"],
                json.dumps(record["details"], default=str),
            )

    async def _publish_nats(self, record: dict[str, Any]) -> None:
        """Публикация аудит-события в NATS (для RECON-подписки)."""
        import json
        try:
            from identity.events import _get_nats_conn
            nc = await _get_nats_conn()
            if nc:
                await nc.publish(
                    f"identity.audit.{record['action']}",
                    json.dumps(record, default=str).encode(),
                )
        except Exception:
            pass  # NATS unavailable — not critical for audit

    def _write_to_buffer(self, record: dict[str, Any]) -> None:
        """Fallback в in-memory буфер."""
        if len(self._buffer) >= self._max_buffer:
            self._buffer.pop(0)
        self._buffer.append(record)

    async def flush_buffer(self) -> int:
        """Попытаться записать буферизованные события в БД."""
        if not self._buffer:
            return 0
        flushed = 0
        remaining: list[dict[str, Any]] = []
        for record in self._buffer:
            try:
                await self._write_to_db(record)
                flushed += 1
            except Exception:
                remaining.append(record)
        self._buffer = remaining
        if flushed:
            logger.info("Flushed %d identity audit records from buffer", flushed)
        return flushed

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_audit_logger: IdentityAuditLogger | None = None


def get_identity_audit_logger() -> IdentityAuditLogger:
    """Получить единственный экземпляр IdentityAuditLogger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = IdentityAuditLogger()
    return _audit_logger
