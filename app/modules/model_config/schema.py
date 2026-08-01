"""model_config — Pydantic Schema"""

from pydantic import BaseModel, ConfigDict


class ModelConfigCreate(BaseModel):
    """创建请求"""
    pass


class ModelConfigRead(BaseModel):
    """查询响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
