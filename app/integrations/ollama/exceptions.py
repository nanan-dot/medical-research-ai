"""Ollama 本地调用的结构化异常。"""

from app.integrations.llm.exceptions import LLMClientError


class OllamaError(LLMClientError):
    code = "ollama_error"


class OllamaConfigurationError(OllamaError):
    code = "ollama_configuration_error"


class OllamaServiceUnavailableError(OllamaError):
    code = "ollama_service_unavailable"


class OllamaIncompatibleServiceError(OllamaError):
    code = "ollama_incompatible_service"


class OllamaModelNotFoundError(OllamaError):
    code = "ollama_model_not_found"


class OllamaTimeoutError(OllamaError):
    code = "ollama_timeout"


class OllamaResourceError(OllamaError):
    code = "ollama_resource_error"


class OllamaResponseError(OllamaError):
    code = "ollama_response_error"
