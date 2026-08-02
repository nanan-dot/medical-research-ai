"""统一异常定义"""

from typing import Any


class AppError(Exception):
    """业务异常基类"""

    status_code = 400
    code = "application_error"

    def __init__(self, message: str, detail: Any = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class InvalidPathError(AppError):
    status_code = 400
    code = "invalid_path"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"


class TemporarilyUnavailableError(AppError):
    status_code = 503
    code = "temporarily_unavailable"


class AIModelError(AppError):
    """AI 模型调用错误"""

    pass
