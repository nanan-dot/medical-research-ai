"""feedback — Pydantic Schema"""

from pydantic import BaseModel, ConfigDict


class FeedbackCreate(BaseModel):
    """创建请求"""
    pass


class FeedbackRead(BaseModel):
    """查询响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
