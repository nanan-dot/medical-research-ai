"""model_config — 数据模型"""

from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # TODO: 添加业务字段
