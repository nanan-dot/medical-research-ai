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
from app.modules.evidence_matrix.model import (  # noqa: F401
    EvidenceMatrix,
    MatrixCell,
    MatrixDocument,
    MatrixField,
)
from app.modules.research_direction.model import ResearchDirection  # noqa: F401
from app.modules.feasibility.model import FeasibilityScore  # noqa: F401
from app.modules.advisor_workflow.model import AdvisorReview, DirectionRevision  # noqa: F401
from app.modules.presentation.model import Presentation  # noqa: F401
from app.modules.outline.model import Outline  # noqa: F401
from app.modules.writing_project.model import (  # noqa: F401
    WritingGeneratedContent,
    WritingProject,
    WritingUserMaterial,
    WritingVersion,
)
from app.modules.ai_disclosure.model import AIUsageEvent, DisclosureDraft  # noqa: F401
from app.modules.research_conditions.model import (
    ResearchConditions,
    ResearchConditionsVersion,
)
from app.modules.topic_structuring.model import (
    TopicStructuring,
    TopicStructuringVersion,
)
from app.modules.writing.model import Writing
from app.modules.task.model import TaskRecord

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
    "ResearchConditions",
    "ResearchConditionsVersion",
    "TopicStructuring",
    "TopicStructuringVersion",
    "Writing",
    "TaskRecord",
]
