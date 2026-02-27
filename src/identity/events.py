"""
identity/events.py — NATS Event Publisher (Этап 3, шаг 3.5).

Публикует доменные события Identity-сервиса в NATS:
    • ``identity.user.registered``  — новый пользователь зарегистрирован
    • ``identity.org.created``      — создана организация
    • ``identity.org.updated``      — данные организации изменены

RECON подписывается на эти события для обновления денормализованных
полей в таблице ``acts`` (owner_inn/name, counterparty_inn/name).

Graceful degradation: если NATS недоступен — событие пропускается
с предупреждением в лог (не ломает основной бизнес-процесс).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import nats
from nats.aio.client import Client as NATSClient

from identity.config import get_settings

logger = logging.getLogger(__name__)

# ── Singleton NATS connection ─────────────────────────────────────────────

_nc: NATSClient | None = None


async def connect() -> NATSClient | None:
    """Подключается к NATS (если ещё не подключён)."""
    global _nc
    if _nc is not None and _nc.is_connected:
        return _nc
    settings = get_settings()
    try:
        _nc = await nats.connect(settings.nats_url)
        logger.info("NATS publisher connected: %s", settings.nats_url)
        return _nc
    except Exception as exc:
        logger.warning("NATS connect failed (events will be skipped): %s", exc)
        _nc = None
        return None


async def disconnect() -> None:
    """Закрывает соединение с NATS."""
    global _nc
    if _nc and _nc.is_connected:
        await _nc.drain()
        logger.info("NATS publisher disconnected")
    _nc = None


# ── Публикация событий ───────────────────────────────────────────────────

async def publish(subject: str, data: dict[str, Any]) -> None:
    """
    Публикует JSON-событие в NATS.

    Args:
        subject: Тема сообщения (e.g. ``identity.user.registered``).
        data: Payload (сериализуется в JSON).
    """
    nc = await connect()
    if nc is None:
        logger.debug("NATS unavailable — skipping event %s", subject)
        return
    try:
        payload = json.dumps(data, default=str).encode("utf-8")
        await nc.publish(subject, payload)
        logger.info("NATS event published: %s", subject)
    except Exception as exc:
        logger.warning("NATS publish failed for %s: %s", subject, exc)


# ── Удобные функции для Identity-домена ─────────────────────────────────

async def emit_user_registered(user_id: str, email: str, inn: str) -> None:
    """Событие: новый пользователь зарегистрирован."""
    await publish("identity.user.registered", {
        "event": "user.registered",
        "user_id": user_id,
        "email": email,
        "inn": inn,
    })


async def emit_org_created(org_id: str, inn: str, name: str) -> None:
    """Событие: организация создана."""
    await publish("identity.org.created", {
        "event": "org.created",
        "org_id": org_id,
        "inn": inn,
        "name": name,
    })


async def emit_org_updated(org_id: str, inn: str, name: str) -> None:
    """Событие: данные организации обновлены."""
    await publish("identity.org.updated", {
        "event": "org.updated",
        "org_id": org_id,
        "inn": inn,
        "name": name,
    })
