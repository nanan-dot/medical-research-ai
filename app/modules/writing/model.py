"""writing — 数据模型"""

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Writing(Base):
    __tablename__ = "writings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 脚手架遗留：写作业务由 writing_project / writing_ai / writing_review 模块承载，
    # 本模型仅保留 id 以兼容早期 repository 契约。
