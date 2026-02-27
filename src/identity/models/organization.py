"""
identity/models/organization.py — Доменные модели организации.

Перенесено из recon/models/organization.py в рамках Этапа 2 (шаг 2.2).

References:
    - [change.md: Этап 2, шаг 2.2]
    - [RECON TZ: Section 3.1] User and Organization
"""

from uuid import UUID, uuid4

from pydantic import Field

from identity.models.common import IdentityBase
from identity.models.enums import UserRole, UserStatus


class LinkedUser(IdentityBase):
    """Запись о привязке пользователя к организации."""
    user_id: UUID
    role: UserRole = Field(default=UserRole.ACCOUNTANT)
    status: UserStatus = Field(default=UserStatus.PENDING)


class OrganizationCreate(IdentityBase):
    """Схема для создания организации."""
    name: str = Field(..., min_length=1, max_length=512, examples=["ООО «Альфа»"])
    inn: str = Field(..., min_length=10, max_length=12, pattern=r"^\d{10,12}$")
    ogrn: str | None = Field(default=None, min_length=13, max_length=15, pattern=r"^\d{13,15}$")
    email: str | None = Field(default=None, examples=["buh@alfa.ru"])
    phone: str | None = Field(default=None)


class OrganizationRead(IdentityBase):
    """Схема для возврата данных организации."""
    org_id: UUID = Field(default_factory=uuid4)
    name: str
    inn: str
    ogrn: str | None = None
    email: str | None = None
    phone: str | None = None
    linked_users: list[LinkedUser] = Field(default_factory=list)
