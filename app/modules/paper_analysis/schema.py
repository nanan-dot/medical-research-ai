"""paper_analysis — Pydantic Schema"""

from pydantic import BaseModel, ConfigDict


class PaperAnalysisCreate(BaseModel):
    """创建请求"""
    pass


class PaperAnalysisRead(BaseModel):
    """查询响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
