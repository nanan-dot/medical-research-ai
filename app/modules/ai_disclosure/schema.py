"""AI 使用记录的类型契约。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Purpose = Literal["draft", "outline", "polish", "analysis", "translate"]


class AIUsageEventCreate(BaseModel):
    model_name: str = Field(min_length=1, max_length=100)
    model_version: str = Field(min_length=1, max_length=100)
    purpose: Purpose
    input_scope: str = Field(min_length=1, max_length=500)
    output_version: str = Field(min_length=1, max_length=100)
    human_edited: bool = False
    is_cloud: bool = False


class AIUsageEventRead(AIUsageEventCreate):
    id: int
    project_id: int
    event_id: str
    created_at: datetime


class DisclosureDraftRead(BaseModel):
    id: int
    project_id: int
    content: str
    version: int
    created_at: datetime
    updated_at: datetime
