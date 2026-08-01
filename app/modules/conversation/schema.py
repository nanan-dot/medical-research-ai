"""conversation — Pydantic Schema"""

from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    """创建请求"""
    pass


class ConversationRead(BaseModel):
    """查询响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
