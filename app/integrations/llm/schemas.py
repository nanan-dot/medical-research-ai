"""云端模型客户端的数据结构。"""

from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class LLMConfig(BaseModel):
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_base: AnyHttpUrl
    api_key: SecretStr
    timeout_seconds: float = Field(default=30.0, gt=0)

    @property
    def chat_completions_url(self) -> str:
        return f"{str(self.api_base).rstrip('/')}/chat/completions"


class LLMResponse(BaseModel):
    text: str = Field(min_length=1)
    provider: str
    model: str
    elapsed_seconds: float = Field(ge=0)
