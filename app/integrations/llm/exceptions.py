"""不会暴露凭证或供应商响应正文的模型客户端异常。"""


class LLMClientError(Exception):
    """统一模型客户端异常基类。"""

    code = "llm_client_error"

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class LLMConfigurationError(LLMClientError):
    code = "llm_configuration_error"


class LLMAuthenticationError(LLMClientError):
    code = "llm_authentication_error"


class LLMModelNotFoundError(LLMClientError):
    code = "llm_model_not_found"


class LLMRateLimitError(LLMClientError):
    code = "llm_rate_limit_error"


class LLMTimeoutError(LLMClientError):
    code = "llm_timeout_error"


class LLMConnectionError(LLMClientError):
    code = "llm_connection_error"


class LLMProviderError(LLMClientError):
    code = "llm_provider_error"


class LLMResponseFormatError(LLMClientError):
    code = "llm_response_format_error"
