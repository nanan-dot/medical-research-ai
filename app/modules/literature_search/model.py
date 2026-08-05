"""literature_search — 数据模型"""

from datetime import datetime

from sqlalchemy import DateTime, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LiteratureSearch(Base):
    __tablename__ = "literature_searchs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # TODO: 添加业务字段


class LiteratureSearchResult(Base):
    """一次 PubMed 检索执行的持久化结果。

    设计说明：检索结果（含 verified 标记）需要被 BibTeX 导出与前端多次读取，
    因此落库保存；条目序列化为 JSON 存储，保持表结构简单、避免关联表膨胀。
    反幻觉字段 verified/verified_by/verified_on 与条目一起保存，导出时不重新
    计算，确保 BibTeX 与当时检索到的验证状态一致。
    """

    __tablename__ = "literature_search_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    total_count: Mapped[int] = mapped_column(nullable=False, default=0)
    items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
