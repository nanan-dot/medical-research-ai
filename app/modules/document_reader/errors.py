"""阅读器稳定错误码。"""

from app.common.exceptions import ConflictError, NotFoundError


class ReaderRevisionConflictError(ConflictError):
    code = "READER_REVISION_CONFLICT"


class DocumentFileChangedError(ConflictError):
    code = "DOCUMENT_FILE_CHANGED"


class ReaderStateVersionConflictError(ConflictError):
    code = "READER_STATE_VERSION_CONFLICT"

    def __init__(self, current_state: dict[str, object]):
        super().__init__("阅读状态已被更新，请刷新后重试", {"current_state": current_state})


class IdempotencyKeyReusedError(ConflictError):
    code = "IDEMPOTENCY_KEY_REUSED"


class SourceAnchorRelocationRequiredError(ConflictError):
    code = "SOURCE_ANCHOR_RELOCATION_REQUIRED"


class ReaderCapabilityNotReadyError(ConflictError):
    code = "READER_CAPABILITY_NOT_READY"


class ReaderResourceNotFoundError(NotFoundError):
    code = "READER_RESOURCE_NOT_FOUND"

