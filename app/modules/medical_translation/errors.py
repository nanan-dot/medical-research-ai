from app.common.exceptions import ConflictError, UnprocessableEntityError


class TranslationConflictError(ConflictError):
    code = "TRANSLATION_CONFLICT"


class TranslationStateError(ConflictError):
    code = "TRANSLATION_STATE_CONFLICT"


class TranslationBlockedError(UnprocessableEntityError):
    code = "TRANSLATION_BLOCKED"
