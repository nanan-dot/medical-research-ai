"""统一异常定义"""

from typing import Any


class AppError(Exception):
    """业务异常基类"""
    def __init__(self, message: str, detail: Any = None):
        self.message = message
        self.detail = detail


class NotFoundError(AppError):
    pass


class ConflictError(AppError):
    pass


class AIModelError(AppError):
    """AI 模型调用错误"""
    pass
