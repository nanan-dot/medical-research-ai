from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DeploymentMode(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"


class Provider(StrEnum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    OPENROUTER = "openrouter"


class ModelConfigCreate(BaseModel):
    deployment_mode: DeploymentMode
    provider: Provider
    api_base: str = Field(min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=1000)
    model_name: str = Field(min_length=1, max_length=200)
    is_default: bool = False
    allow_cloud_content: bool = False

    @model_validator(mode="after")
    def validate_privacy(self):
        if (
            self.provider == Provider.OLLAMA
            and self.deployment_mode != DeploymentMode.LOCAL
        ):
            raise ValueError("Ollama must use local mode")
        if (
            self.provider != Provider.OLLAMA
            and self.deployment_mode == DeploymentMode.LOCAL
        ):
            raise ValueError("Cloud providers cannot use local mode")
        if self.provider != Provider.OLLAMA and not self.api_key:
            raise ValueError("Cloud provider API key is required")
        if (
            self.deployment_mode in {DeploymentMode.CLOUD, DeploymentMode.HYBRID}
            and not self.allow_cloud_content
        ):
            raise ValueError("Cloud content transfer must be explicitly authorized")
        return self


class ModelConfigRead(BaseModel):
    id: int
    deployment_mode: DeploymentMode
    provider: Provider
    api_base: str
    model_name: str
    is_default: bool
    allow_cloud_content: bool
    api_key_masked: str | None


class ConnectionTestRequest(BaseModel):
    acknowledge_possible_cost: bool = False


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
