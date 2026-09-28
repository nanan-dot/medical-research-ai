"""Stable note-library domain errors."""

from app.common.exceptions import AppError


class NoteLibraryError(AppError):
    """Error safe for the public note-library envelope."""

    def __init__(
        self, code: str, message: str, *, status_code: int = 409, detail: object = None
    ) -> None:
        super().__init__(message, detail)
        self.code = code
        self.status_code = status_code
