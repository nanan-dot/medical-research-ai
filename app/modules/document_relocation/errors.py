"""A3 errors contain stable codes and never include document text."""

from app.common.exceptions import ConflictError


class RelocationError(ConflictError):
    def __init__(
        self, code: str, message: str = "原文重定位状态已变化，请刷新后重试"
    ) -> None:
        self.code = code
        super().__init__(message)


__all__ = ["RelocationError"]
