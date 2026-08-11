"""health — 数据模型"""

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Health(Base):
    __tablename__ = "healths"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 脚手架遗留：当前仅有 id 主键，健康检查由 /health 端点直接返回状态，
    # 无业务字段需要持久化；repository.get 保留以兼容早期契约。
