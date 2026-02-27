"""
═══════════════════════════════════════════════════════════════════════════════
Identity — Иерархия доменных ошибок (Custom Exception Hierarchy)
═══════════════════════════════════════════════════════════════════════════════

Собственная иерархия исключений Identity-микросервиса.
Базовый класс ``IdentityError`` (вместо ``ReconError``).
HTTP-маппинг кодов выполняется в ``identity.main:identity_error_handler``.

Создано в рамках Этапа 3, шаг 3.1 (change.md §5).
"""


class IdentityError(Exception):
    """
    Базовое исключение для всех доменных ошибок Identity.

    Атрибуты
    ────────
        message (str):  Описание ошибки. Передаётся клиенту в JSON.
        code (str):     Строковый код. Используется для маппинга на HTTP-статус.
        details (dict): Дополнительные данные (entity, id и т.д.).
    """

    def __init__(
        self,
        message: str,
        code: str = "IDENTITY_ERROR",
        details: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(IdentityError):
    """Ошибка аутентификации: 401 Unauthorized."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="IDENTITY_AUTH_ERROR")


class AuthorizationError(IdentityError):
    """Ошибка авторизации: 403 Forbidden."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="IDENTITY_AUTHZ_ERROR")


class NotFoundError(IdentityError):
    """Сущность не найдена: 404 Not Found."""

    def __init__(self, entity: str, entity_id: str):
        super().__init__(
            message=f"{entity} not found: {entity_id}",
            code="IDENTITY_NOT_FOUND",
            details={"entity": entity, "id": entity_id},
        )


class ConflictError(IdentityError):
    """Конфликт с текущим состоянием: 409 Conflict."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="IDENTITY_CONFLICT", details=details)


class ValidationError(IdentityError):
    """Ошибка доменной валидации: 422 Unprocessable Entity."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="IDENTITY_VALIDATION_ERROR", details=details)


__all__ = [
    "IdentityError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
]
