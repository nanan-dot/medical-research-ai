"""knowledge_source — 数据模型"""

from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # TODO: 添加业务字段
