"""
identity/services/rbac.py — RBAC для Identity-микросервиса.

Содержит роли, иерархию ролей и Identity-permissions.
Перенесено из recon/services/rbac_identity.py (TD-2, change.md §10.2).

Позволяет Identity-сервису при автономном запуске проверять permissions
без зависимости от recon.*.
"""

from __future__ import annotations

import logging
from enum import Enum

from fastapi import Depends, HTTPException, status

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Роли и иерархия
# ═══════════════════════════════════════════════════════════════════════════════

class Role(str, Enum):
    ADMIN = "admin"
    DIRECTOR = "director"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


ROLE_HIERARCHY: dict[str, int] = {
    Role.VIEWER: 0,
    Role.ACCOUNTANT: 1,
    Role.DIRECTOR: 2,
    Role.ADMIN: 3,
}


# ═══════════════════════════════════════════════════════════════════════════════
# Identity Permissions
# ═══════════════════════════════════════════════════════════════════════════════

IDENTITY_PERMISSIONS: dict[str, str] = {
    "org.create": "director",
    "org.read": "viewer",
    "org.update": "director",
    "org.link_user": "director",
    "admin.manage_users": "admin",
    "admin.manage_roles": "admin",
    "admin.system_config": "admin",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ═══════════════════════════════════════════════════════════════════════════════

def has_role(user, required_role: str) -> bool:
    """Проверяет, имеет ли пользователь достаточный уровень роли."""
    user_role = getattr(user, "role", None) or Role.VIEWER
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


def has_permission(user, permission: str) -> bool:
    """Проверяет, имеет ли пользователь указанное разрешение."""
    required_role = IDENTITY_PERMISSIONS.get(permission)
    if required_role is None:
        logger.warning("Unknown permission requested: %s", permission)
        return False
    return has_role(user, required_role)


def require_role(role: str):
    """FastAPI dependency: требует минимальную роль."""
    from identity.dependencies import get_current_user

    async def _check(user=Depends(get_current_user)) -> None:
        if not has_role(user, role):
            logger.warning(
                "RBAC: user %s denied role=%s",
                getattr(user, "user_id", "?"), role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
    return _check


def require_permission(permission: str):
    """FastAPI dependency: требует конкретное разрешение."""
    from identity.dependencies import get_current_user

    async def _check(user=Depends(get_current_user)) -> None:
        if not has_permission(user, permission):
            logger.warning(
                "RBAC: user %s denied permission '%s'",
                getattr(user, "user_id", "?"), permission,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
    return _check
