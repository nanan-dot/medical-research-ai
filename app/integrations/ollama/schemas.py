"""Ollama 服务状态、模型和资源结构。"""

from pydantic import BaseModel, Field


class OllamaStatus(BaseModel):
    version: str = Field(min_length=1)


class OllamaModelInfo(BaseModel):
    name: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)


class OllamaResourceUsage(BaseModel):
    model: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    size_vram_bytes: int = Field(ge=0)
