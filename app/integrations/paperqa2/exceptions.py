"""Sanitized PaperQA2 errors that do not expose external objects or document text."""

from app.common.exceptions import AppError


class PaperQA2Error(AppError):
    code = "paperqa2_error"


class PaperQA2ConfigurationError(PaperQA2Error):
    code = "paperqa2_configuration_error"


class PaperQA2NotInstalledError(PaperQA2Error):
    code = "paperqa2_not_installed"


class PaperQA2VersionError(PaperQA2Error):
    code = "paperqa2_version_error"


class PaperQA2DocumentError(PaperQA2Error):
    code = "paperqa2_document_error"


class PaperQA2IndexNotFoundError(PaperQA2Error):
    code = "paperqa2_index_not_found"


class PaperQA2IndexCorruptError(PaperQA2Error):
    code = "paperqa2_index_corrupt"


class PaperQA2ResponseError(PaperQA2Error):
    code = "paperqa2_response_error"


class PaperQA2OperationError(PaperQA2Error):
    code = "paperqa2_operation_error"
