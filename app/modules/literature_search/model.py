"""literature_search — 数据模型"""

from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LiteratureSearch(Base):
    __tablename__ = "literature_searchs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # TODO: 添加业务字段
