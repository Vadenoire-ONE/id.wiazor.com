"""
═══════════════════════════════════════════════════════════════════════════════
Identity — In-Memory хранилище (замена Identity DB для локальной разработки)
═══════════════════════════════════════════════════════════════════════════════

Собственный memory store Identity-микросервиса.
Содержит in-memory реализации user_repo и org_repo +
функцию ``activate_identity_memory_store()`` для monkey-patching.

Перенесено из recon/identity_memory_store.py (Этап 3, шаг 3.1).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Хранилища данных Identity-домена
# ═══════════════════════════════════════════════════════════════════════════════
_users: dict[UUID, dict] = {}
_orgs: dict[UUID, dict] = {}
_org_users: list[dict] = []

_now = lambda: datetime.now(timezone.utc)  # noqa: E731


# ═══════════════════════════════════════════════════════════════════════════════
# user_repo in-memory
# ═══════════════════════════════════════════════════════════════════════════════

async def create_user(
    full_name: str, inn: str, email: str, phone: str, password_hash: str,
) -> dict:
    """Создаёт нового пользователя в памяти."""
    uid = uuid4()
    now = _now()
    user = {
        "user_id": uid, "full_name": full_name, "inn": inn,
        "email": email, "phone": phone, "password_hash": password_hash,
        "status": "pending", "created_at": now, "updated_at": now,
    }
    _users[uid] = user
    logger.info("Identity memory store: created user %s <%s>", full_name, email)
    return user


async def get_user_by_id(user_id: UUID) -> dict | None:
    return _users.get(user_id)


async def get_user_by_email(email: str) -> dict | None:
    for u in _users.values():
        if u["email"] == email:
            return u
    return None


async def get_user_by_inn(inn: str) -> dict | None:
    for u in _users.values():
        if u["inn"] == inn:
            return u
    return None


async def update_user_status(user_id: UUID, status: str) -> None:
    if user_id in _users:
        _users[user_id]["status"] = status
        _users[user_id]["updated_at"] = _now()


# ═══════════════════════════════════════════════════════════════════════════════
# org_repo in-memory
# ═══════════════════════════════════════════════════════════════════════════════

async def create_organization(
    name: str, inn: str, ogrn: str | None = None,
    email: str | None = None, phone: str | None = None,
) -> dict:
    """Создаёт новую организацию в памяти."""
    oid = uuid4()
    now = _now()
    org = {
        "org_id": oid, "name": name, "inn": inn, "ogrn": ogrn,
        "email": email, "phone": phone, "created_at": now, "updated_at": now,
    }
    _orgs[oid] = org
    logger.info("Identity memory store: created org %s (INN %s)", name, inn)
    return org


async def link_user_to_org(
    org_id: UUID, user_id: UUID, role: str = "accountant",
) -> None:
    _org_users.append({
        "org_id": org_id, "user_id": user_id,
        "role": role, "joined_at": _now(),
    })


async def get_orgs_for_user(user_id: UUID) -> list[dict]:
    org_ids = [ou["org_id"] for ou in _org_users if ou["user_id"] == user_id]
    return [_orgs[oid] for oid in org_ids if oid in _orgs]


async def get_org_by_id(org_id: UUID) -> dict | None:
    return _orgs.get(org_id)


async def get_linked_users(org_id: UUID) -> list[dict]:
    user_ids = [ou["user_id"] for ou in _org_users if ou["org_id"] == org_id]
    result = []
    for uid in user_ids:
        u = _users.get(uid)
        if u:
            safe = {k: v for k, v in u.items() if k != "password_hash"}
            result.append(safe)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Активация in-memory хранилища (monkey-patching)
# ═══════════════════════════════════════════════════════════════════════════════

def activate_identity_memory_store() -> None:
    """
    Подменяет функции в identity.db.repositories.* на in-memory реализации.

    Вызывается из identity.main → lifespan() при недоступности Identity DB.
    """
    from identity.db.repositories import user_repo, org_repo

    # ── user_repo ──
    user_repo.create_user = create_user
    user_repo.get_user_by_id = get_user_by_id
    user_repo.get_user_by_email = get_user_by_email
    user_repo.get_user_by_inn = get_user_by_inn
    user_repo.update_user_status = update_user_status

    # ── org_repo ──
    org_repo.create_organization = create_organization
    org_repo.link_user_to_org = link_user_to_org
    org_repo.get_orgs_for_user = get_orgs_for_user
    org_repo.get_org_by_id = get_org_by_id
    org_repo.get_linked_users = get_linked_users

    logger.warning(
        "🧠 Identity memory store ACTIVATED — all data is in-memory (lost on restart)."
    )
