"""health — Pydantic Schema"""

from pydantic import BaseModel, ConfigDict


class HealthCreate(BaseModel):
    """创建请求"""
    pass


class HealthRead(BaseModel):
    """查询响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
