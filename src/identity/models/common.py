"""
identity/models/common.py — Базовые типы Identity-домена.

Identity использует собственную базовую модель IdentityBase, которая
наследует конфигурацию от ReconBase для совместимости, но может быть
заменена при полном отделении (Этап 3).

References:
    - [change.md: Этап 2, шаг 2.2]
"""

from pydantic import BaseModel


class IdentityBase(BaseModel):
    """Базовая Pydantic-модель для Identity-схем."""

    model_config = {"str_strip_whitespace": True}
