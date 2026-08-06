"""集中注册所有 SQLAlchemy 模型。

Alembic 和元数据测试导入本模块，以确保所有模型都挂载到同一个
``Base.metadata``。业务代码仍从各自模块导入模型。
"""

from app.modules.conversation.model import Conversation
from app.modules.document.model import Document
from app.modules.evaluation.model import Evaluation
from app.modules.feedback.model import Feedback
from app.modules.export.model import ExportRecord
from app.modules.health.model import Health
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.library_item.model import LibraryItem
from app.modules.literature_search.model import (
    LiteratureDuplicateGroup,
    LiteratureDuplicateGroupMember,
    LiteratureDuplicateResolution,
    LiteratureReadingOrder,
    LiteratureSearch,
    LiteratureSearchItemState,
    LiteratureSearchResult,
    LiteratureSearchResultVersion,
    LiteratureSearchTask,
)
from app.modules.model_config.model import ModelConfig
from app.modules.paper_analysis.model import PaperAnalysis
from app.modules.comparison.model import ComparisonCell, ComparisonTask  # noqa: F401
from app.modules.research_direction.model import ResearchDirection
from app.modules.writing.model import Writing

__all__ = [
    "Conversation",
    "Document",
    "Evaluation",
    "Feedback",
    "ExportRecord",
    "Health",
    "KnowledgeSource",
    "LibraryItem",
    "LiteratureDuplicateGroup",
    "LiteratureDuplicateGroupMember",
    "LiteratureDuplicateResolution",
    "LiteratureReadingOrder",
    "LiteratureSearch",
    "LiteratureSearchItemState",
    "LiteratureSearchResult",
    "LiteratureSearchResultVersion",
    "LiteratureSearchTask",
    "ModelConfig",
    "PaperAnalysis",
    "ResearchDirection",
    "Writing",
]
