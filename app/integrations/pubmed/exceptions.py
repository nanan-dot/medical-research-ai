"""PubMed E-utilities 调用的结构化异常。

所有异常继承 AppError，避免把 httpx/标准库异常的原始信息直接暴露给上层。
"""

from app.common.exceptions import AppError


class PubMedError(AppError):
    code = "pubmed_error"


class PubMedConfigurationError(PubMedError):
    code = "pubmed_configuration_error"


class PubMedRateLimitError(PubMedError):
    """NCBI 返回 HTTP 429 或重试耗尽时抛出。"""

    code = "pubmed_rate_limit"


class PubMedTimeoutError(PubMedError):
    code = "pubmed_timeout"


class PubMedConnectionError(PubMedError):
    code = "pubmed_connection_error"


class PubMedResponseError(PubMedError):
    """响应结构不符合预期（含非法 XML / 非法 JSON）。"""

    code = "pubmed_response_error"


class PubMedOperationError(PubMedError):
    """调用过程发生非预期的内部错误。"""

    code = "pubmed_operation_error"
