"""
identity/models/user.py — Доменные модели пользователя (ФЛ).

Перенесено из recon/models/user.py в рамках Этапа 2 (шаг 2.2).
Используют Identity-собственные базовые типы.

References:
    - [change.md: Этап 2, шаг 2.2]
    - [RECON TZ: Section 3.1] User and Organization
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from identity.models.common import IdentityBase
from identity.models.enums import VerificationMethod


class UserVerification(BaseModel):
    """Детали верификации ФЛ-пользователя."""
    method: VerificationMethod
    ecp_sn: str | None = Field(default=None, description="ECP serial number")
    payment_id: str | None = Field(default=None, description="Identifying payment ID")


class UserCreate(IdentityBase):
    """Схема для регистрации нового ФЛ-пользователя."""
    full_name: str = Field(..., min_length=2, max_length=255, examples=["Иванов Иван Иванович"])
    inn: str = Field(..., min_length=10, max_length=12, pattern=r"^\d{10,12}$")
    email: str = Field(..., examples=["user@example.com"])
    phone: str = Field(..., pattern=r"^\+7[\- ]?\d{3}[\- ]?\d{3}[\- ]?\d{2}[\- ]?\d{2}$", examples=["+7-900-000-00-00"])
    password: str = Field(..., min_length=8, max_length=128)


class UserRead(IdentityBase):
    """Схема для возврата данных пользователя (без пароля)."""
    user_id: UUID = Field(default_factory=uuid4)
    full_name: str
    inn: str
    email: str
    phone: str = ""
    status: str = "pending"
    role: str = "viewer"
    verification: UserVerification | None = None
    created_at: datetime | None = None
