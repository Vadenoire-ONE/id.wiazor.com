"""
identity/adapters/egrul_client.py — Клиент ЕГРЮЛ (Identity).

Перенесено из recon/adapters/egrul_client.py в рамках Этапа 2 (шаг 2.2).
Заглушка — в production необходимо подключить реальный API.

References:
    - [change.md: Этап 2, шаг 2.2]
"""

from __future__ import annotations

import logging

import httpx  # noqa: F401

logger = logging.getLogger(__name__)

EGRUL_API_URL = "https://egrul.nalog.ru"  # placeholder


async def lookup_by_inn(inn: str) -> dict | None:
    """
    Поиск организации в ЕГРЮЛ/ЕГРИП по ИНН.

    ⚠ ЗАГЛУШКА — всегда возвращает None.
    """
    logger.info("Запрос к ЕГРЮЛ по ИНН %s (заглушка)", inn)
    return None
