"""knowledge_source — Pydantic Schema"""

from pydantic import BaseModel, ConfigDict


class KnowledgeSourceCreate(BaseModel):
    """创建请求"""
    pass


class KnowledgeSourceRead(BaseModel):
    """查询响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
