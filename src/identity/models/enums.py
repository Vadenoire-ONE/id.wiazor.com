"""
identity/models/enums.py — Перечисления Identity-домена.

Содержит enum'ы, относящиеся к пользователям и организациям:
    • UserRole — роль пользователя в организации
    • UserStatus — статус привязки к организации
    • VerificationMethod — способ верификации ФЛ

References:
    - [change.md: Этап 2, шаг 2.2]
    - Перенесено из recon/models/identity_enums.py
"""

from enum import Enum


class UserRole(str, Enum):
    """Роль пользователя в организации."""
    DIRECTOR = "director"
    ACCOUNTANT = "accountant"
    AGENT = "agent"


class UserStatus(str, Enum):
    """Статус привязки пользователя к организации."""
    APPROVED = "approved"
    PENDING = "pending"


class VerificationMethod(str, Enum):
    """Способ верификации ФЛ-пользователя."""
    ECP = "ecp"
    PAYMENT = "payment"
    MIXED = "mixed"
