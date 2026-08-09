"""writing — Pydantic Schema"""

from pydantic import BaseModel, ConfigDict


class WritingCreate(BaseModel):
    """创建请求"""



class WritingRead(BaseModel):
    """查询响应"""

    model_config = ConfigDict(from_attributes=True)
    id: int
