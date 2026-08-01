"""evaluation — Pydantic Schema"""

from pydantic import BaseModel, ConfigDict


class EvaluationCreate(BaseModel):
    """创建请求"""
    pass


class EvaluationRead(BaseModel):
    """查询响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
