"""检索策略、不可变修订与执行记录。"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LiteratureSearchStrategy(Base):
    __tablename__="literature_search_strategies"
    id:Mapped[int]=mapped_column(primary_key=True,autoincrement=True)
    name:Mapped[str]=mapped_column(String(300),nullable=False)
    research_context_id:Mapped[int|None]=mapped_column(ForeignKey("research_contexts.id",ondelete="SET NULL"),index=True)
    framework:Mapped[str]=mapped_column(String(32),nullable=False,default="topic")
    database:Mapped[str]=mapped_column(String(32),nullable=False,default="pubmed")
    is_pinned:Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    is_archived:Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    copied_from_strategy_id:Mapped[int|None]=mapped_column(ForeignKey("literature_search_strategies.id",ondelete="SET NULL"))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text("CURRENT_TIMESTAMP"))
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text("CURRENT_TIMESTAMP"))
    archived_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class LiteratureSearchStrategyVersion(Base):
    __tablename__="literature_search_strategy_versions"
    __table_args__=(UniqueConstraint("strategy_id","version",name="uq_literature_strategy_version"),)
    id:Mapped[int]=mapped_column(primary_key=True,autoincrement=True)
    strategy_id:Mapped[int]=mapped_column(ForeignKey("literature_search_strategies.id",ondelete="CASCADE"),index=True)
    version:Mapped[int]=mapped_column(Integer,nullable=False)
    original_query:Mapped[str]=mapped_column(Text,nullable=False)
    structured_query:Mapped[str]=mapped_column(Text,nullable=False,default="")
    search_string:Mapped[str]=mapped_column(Text,nullable=False)
    filters:Mapped[str]=mapped_column(Text,nullable=False,default="")
    model_version:Mapped[str]=mapped_column(String(200),nullable=False)
    user_edits:Mapped[str]=mapped_column(Text,nullable=False,default="")
    term_groups_json:Mapped[str]=mapped_column(Text,nullable=False,default="[]")
    mesh_terms_json:Mapped[str]=mapped_column(Text,nullable=False,default="[]")
    start_year:Mapped[int|None]=mapped_column(Integer)
    end_year:Mapped[int|None]=mapped_column(Integer)
    change_summary_json:Mapped[str]=mapped_column(Text,nullable=False,default="{}")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text("CURRENT_TIMESTAMP"))

class LiteratureSearchExecution(Base):
    __tablename__="literature_search_executions"
    id:Mapped[int]=mapped_column(primary_key=True,autoincrement=True)
    strategy_version_id:Mapped[int]=mapped_column(ForeignKey("literature_search_strategy_versions.id",ondelete="CASCADE"),index=True)
    result_id:Mapped[int|None]=mapped_column(ForeignKey("literature_search_results.id",ondelete="SET NULL"))
    status:Mapped[str]=mapped_column(String(32),nullable=False)
    requested_retmax:Mapped[int]=mapped_column(Integer,nullable=False,default=20)
    result_count:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    previous_result_id:Mapped[int|None]=mapped_column(ForeignKey("literature_search_results.id",ondelete="SET NULL"))
    added_count:Mapped[int|None]=mapped_column(Integer)
    removed_count:Mapped[int|None]=mapped_column(Integer)
    added_pmids_json:Mapped[str|None]=mapped_column(Text)
    removed_pmids_json:Mapped[str|None]=mapped_column(Text)
    has_changes:Mapped[bool|None]=mapped_column(Boolean)
    error_message:Mapped[str|None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text("CURRENT_TIMESTAMP"))
    completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

