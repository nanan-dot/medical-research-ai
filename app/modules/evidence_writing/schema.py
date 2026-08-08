"""证据驱动写作的请求契约。"""

from pydantic import BaseModel, Field

from app.modules.writing_project.schema import GeneratedContent


class OutlineRequest(BaseModel):
    content: GeneratedContent
    expected_version: int = Field(gt=0)
    confirmed: bool = False


class DraftRequest(BaseModel):
    content: GeneratedContent
    expected_version: int = Field(gt=0)


class PolishRequest(BaseModel):
    content: GeneratedContent
    expected_version: int = Field(gt=0)
