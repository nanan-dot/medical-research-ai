"""literature_search — 数据模型"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LiteratureSearch(Base):
    __tablename__ = "literature_searchs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # TODO: 添加业务字段


class LiteratureSearchTask(Base):
    """一次可复现的 PubMed 检索任务（R2-WP04）。

    设计说明：任务表保存的是检索过程的"输入快照"——原始主题、结构化条件、
    检索式、筛选、模型版本与用户修改——而不是检索结果本身。结果通过
    result_versions 关联到 WP03.5 的 LiteratureSearchResult，避免把 items_json
    复制进任务表造成数据膨胀（处理"历史记录过大"）。每次重跑产生一个新版本，
    旧版本保留，任务按创建时间倒序分页展示。

    status 状态机：pending → running → succeeded / failed；失败仅发生在执行层
    （PubMedExecutor.execute 抛出异常），不会伪造结果。
    """

    __tablename__ = "literature_search_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 原始自然语言主题（如"胃癌 EGFR 免疫治疗"），用户输入原文。
    original_query: Mapped[str] = mapped_column(Text, nullable=False)
    # 结构化条件：parse-query 输出的 SearchIntentCandidate 序列化快照，可为空串。
    structured_query: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 检索式：实际发往 PubMed 的布尔查询串。
    search_string: Mapped[str] = mapped_column(Text, nullable=False)
    # 数据库名（当前仅 pubmed；枚举常量见 schema.SearchDatabase）。
    database: Mapped[str] = mapped_column(Text, nullable=False, default="pubmed")
    # 结果总数（最近一次成功执行后的 ESearch 命中数）。
    result_count: Mapped[int] = mapped_column(nullable=False, default=0)
    # 单次执行拉取的条目上限（ESearch retmax），重跑时复用保证结果可复现。
    retmax: Mapped[int] = mapped_column(nullable=False, default=20)
    # 筛选条件（检索式之外的结构化筛选，如语言/年份/研究类型）。
    filters: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 模型版本：候选解析/词项扩展所用模型标识；来源为真实配置，不为空。
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    # 用户修改：对结构化条件、词项组的编辑记录（原始词→替换词映射）。
    user_edits: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 任务状态机。
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    # 失败原因（status=failed 时填充；成功/运行中为空）。
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    # 最近一次执行完成时间（创建/重跑成功后刷新）。
    searched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # 最近一次成功执行对应的结果版本 id（冗余外键，便于列表页直接展示）。
    latest_result_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("literature_search_results.id"), nullable=True
    )
    # 任务关联的全部结果版本，按创建时间排序即为版本顺序。
    result_versions: Mapped[list["LiteratureSearchResultVersion"]] = relationship(
        "LiteratureSearchResultVersion",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="LiteratureSearchResultVersion.created_at",
    )


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


class LiteratureSearchResultVersion(Base):
    """任务到结果版本的关联（任务 <-> 结果 多对多，版本不可变）。

    设计说明：用显式关联表而非在 LiteratureSearchResult 上加 task_id 外键，
    是因为同一结果记录可能被多个任务复用（任务之间可共享搜索策略），且任务
    重跑会追加新版本而绝不修改旧版本。version 序号从 1 开始，由 repository
    在创建时按任务现有版本数 +1 分配；created_at 记录每次检索发生的时间。
    """

    __tablename__ = "literature_search_task_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("literature_search_tasks.id"), nullable=False
    )
    result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("literature_search_results.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    task: Mapped[LiteratureSearchTask] = relationship(back_populates="result_versions")


class LiteratureSearchItemState(Base):
    """检索结果的用户态（manage-refs 融合）：saved / read_status / tags。

    设计说明：items_json 是检索时刻的只读快照，用户"已保存/已读/标签"属于
    个人工作状态，写入该表而不是回写快照，避免污染可复现的检索记录。主键
    用 result_id + pmid 复合键（同一结果快照内 PMID 唯一）；result 删除时
    级联清理用户态，避免孤儿数据。tags 与 custom_order 存 JSON 字符串。
    """

    __tablename__ = "literature_search_item_state"

    result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("literature_search_results.id", ondelete="CASCADE"),
        primary_key=True,
    )
    pmid: Mapped[str] = mapped_column(Text, primary_key=True)
    saved: Mapped[bool] = mapped_column(nullable=False, default=False)
    read_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="unread"
    )
    tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # 用户自定义排序序号（custom 排序使用）：由用户拖拽顺序写入，同一结果内
    # 每条记录保存自己的序号，避免在每个条目上冗余存全量 PMID 顺序列表。
    custom_order_index: Mapped[int | None] = mapped_column(nullable=True)
