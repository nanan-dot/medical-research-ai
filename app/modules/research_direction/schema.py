"""research_direction — Pydantic Schema"""

from pydantic import BaseModel, ConfigDict


class ResearchDirectionCreate(BaseModel):
    """创建请求"""
    pass


class ResearchDirectionRead(BaseModel):
    """查询响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
