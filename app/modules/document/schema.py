"""document — Pydantic Schema"""

from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    """创建请求"""
    pass


class DocumentRead(BaseModel):
    """查询响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
