"""Safe selection errors never echo document text."""

from app.common.exceptions import ConflictError


class SelectionError(ConflictError):
    def __init__(
        self, code: str, message: str = "选区无法精确解析，请刷新原文并重新选择"
    ) -> None:
        self.code = code
        super().__init__(message)
