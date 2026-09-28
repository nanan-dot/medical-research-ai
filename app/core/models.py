"""集中注册所有 SQLAlchemy 模型。

Alembic 和元数据测试导入本模块，以确保所有模型都挂载到同一个
``Base.metadata``。业务代码仍从各自模块导入模型。
"""

from app.modules.advisor_workflow.model import (  # noqa: F401
    AdvisorReview,
    DirectionRevision,
)
from app.agents.authorization_model import ModelTransferAuthorizationRecord  # noqa: F401
from app.agents.artifact_model import (  # noqa: F401
    AgentArtifactRecord,
    ArtifactDependencyRecord,
    InvalidationRecord,
)
from app.agents.budget_model import (  # noqa: F401
    AgentBudgetReservationRecord,
    AgentRootBudgetRecord,
)
from app.agents.confirmation_model import (  # noqa: F401
    AgentRoleQualificationRecord,
    ResearchContextMembershipRecord,
    RoleDecisionRecord,
    UserConfirmationRecord,
)
from app.agents.idempotency_model import AgentIdempotencyRecord  # noqa: F401
from app.agents.model import AgentRunRecord  # noqa: F401
from app.agents.outbox_model import AgentOutboxRecord  # noqa: F401
from app.agents.runtime_model import (  # noqa: F401
    AgentExternalExecutionRecord,
    AgentEventRecord,
    AgentStepRecord,
    AgentTaskRequestRecord,
)
from app.modules.ai_disclosure.model import AIUsageEvent, DisclosureDraft  # noqa: F401
from app.modules.comparison.model import ComparisonCell, ComparisonTask  # noqa: F401
from app.modules.conversation.model import Conversation
from app.modules.document.model import Document
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourcePage,
    DocumentSourceTextItem,
)
from app.modules.document_annotation.model import DocumentAnnotation
from app.modules.document_layout.model import (  # noqa: F401
    DocumentLayoutBlock,
    DocumentLayoutFragment,
    DocumentLayoutSection,
    DocumentLayoutSegment,
    DocumentSegmentationRevision,
)
from app.modules.document_ocr.model import DocumentOcrJob, DocumentOcrPage
from app.modules.document_reader.model import (  # noqa: F401
    PaperReaderState,
    ReaderBookmark,
    ReaderIdempotencyRecord,
    ReaderPageExposure,
    ReaderPreference,
    ReaderQuestion,
    ReaderSession,
    ResearchMaterialCandidate,
)
from app.modules.document_relocation.model import (  # noqa: F401
    AssetAnchorLink,
    DocumentAnchorRelocation,
    DocumentAnchorRelocationDecision,
    DocumentFileRevision,
    LegacyAnchorBackfillItem,
    LegacyAnchorBackfillRun,
)
from app.modules.document_selection.model import (  # noqa: F401
    DocumentAnchorSegment,
    DocumentReadingNote,
    SelectionOperation,
)
from app.modules.document_upload.model import DocumentAsset
from app.modules.evaluation.model import (
    Evaluation,
    EvaluationRunRecord,
    EvaluationRunResult,
)
from app.modules.evidence_matrix.model import (  # noqa: F401
    EvidenceMatrix,
    MatrixCell,
    MatrixDocument,
    MatrixField,
)
from app.modules.export.model import ExportRecord
from app.modules.feasibility.model import FeasibilityScore  # noqa: F401
from app.modules.feedback.model import Feedback
from app.modules.health.model import Health
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.library.model import DocumentAccess, ZoteroCollection, ZoteroLibrary
from app.modules.library_item.model import LibraryItem
from app.modules.library_item.open_fulltext_model import OpenFulltextAcquisition
from app.modules.literature_scoring.model import (  # noqa: F401
    LiteratureArticleScore,
    LiteratureResearchIntentSnapshot,
    LiteratureScoreGeneration,
)
from app.modules.literature_search.history_strategy_model import (  # noqa: F401
    LiteratureSearchExecution,
    LiteratureSearchStrategy,
    LiteratureSearchStrategyVersion,
)
from app.modules.literature_search.model import (
    JournalMetricImportBatch,
    LiteratureCommercialJournalMetric,
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
from app.modules.literature_search.status_model import LiteratureStatusRecord
from app.modules.literature_search.strategy_model import (
    SearchStrategyDraft,
    SearchStrategyMeshTerm,
    SearchStrategyTerm,
    SearchStrategyVersion,
)
from app.modules.medical_translation.model import (  # noqa: F401
    MedicalTranslationJob,
    TranslationReview,
    TranslationRevision,
    TranslationTermOverride,
    TranslationValidationReport,
)
from app.modules.model_config.model import ModelConfig
from app.modules.note_library.model import (  # noqa: F401
    NoteActivity,
    NoteAISuggestion,
    NoteDerivation,
    NoteDraft,
    NoteLegacyBackfill,
    NoteResearchLink,
    NoteRevision,
    NoteSaveOperation,
    NoteSourceLink,
    NoteTag,
    NoteTagLink,
    ResearchNote,
)
from app.modules.outline.model import Outline  # noqa: F401
from app.modules.paper_analysis.model import PaperAnalysis
from app.modules.paper_library.model import (
    PaperActivity,
    PaperLibraryMember,
    PaperResearchCenterPreference,
    PaperResearchRelation,
    PaperTag,
    PaperWorkState,
)
from app.modules.presentation.model import Presentation  # noqa: F401
from app.modules.reading_plan.model import ReadingPlan, ReadingPlanItem
from app.modules.recommendation.model import (
    RecommendationCandidate,
    RecommendationDecision,
    RecommendationNarrationLease,
    RecommendationRun,
)
from app.modules.research_conditions.model import (
    ResearchConditions,
    ResearchConditionsVersion,
)
from app.modules.research_context.model import ResearchContext, ResearchContextDocument
from app.modules.research_direction.model import ResearchDirection
from app.modules.task.model import TaskRecord
from app.modules.topic_structuring.model import (
    TopicStructuring,
    TopicStructuringVersion,
)
from app.modules.writing.model import Writing
from app.modules.unified_conversation.model import KnowledgeGap, UnifiedTurn  # noqa: F401
from app.modules.writing_ai.model import WritingAiSuggestion  # noqa: F401
from app.modules.writing_project.model import (  # noqa: F401
    WritingEvidenceReference,
    WritingGeneratedContent,
    WritingProject,
    WritingUserMaterial,
    WritingVersion,
)
from app.modules.writing_review.model import WritingReview  # noqa: F401

__all__ = [
    "Conversation",
    "Document",
    "DocumentAccess",
    "DocumentAnchorRevision",
    "DocumentAnnotation",
    "DocumentAsset",
    "DocumentOcrJob",
    "DocumentOcrPage",
    "DocumentSourcePage",
    "DocumentSourceTextItem",
    "Evaluation",
    "EvaluationRunRecord",
    "EvaluationRunResult",
    "ExportRecord",
    "Feedback",
    "Health",
    "JournalMetricImportBatch",
    "KnowledgeSource",
    "LibraryItem",
    "LiteratureCommercialJournalMetric",
    "LiteratureDuplicateGroup",
    "LiteratureDuplicateGroupMember",
    "LiteratureDuplicateResolution",
    "LiteratureReadingOrder",
    "LiteratureSearch",
    "LiteratureSearchItemState",
    "LiteratureSearchResult",
    "LiteratureSearchResultVersion",
    "LiteratureSearchTask",
    "LiteratureStatusRecord",
    "MedicalTranslationJob",
    "ModelConfig",
    "OpenFulltextAcquisition",
    "PaperActivity",
    "PaperAnalysis",
    "PaperLibraryMember",
    "PaperResearchCenterPreference",
    "PaperResearchRelation",
    "PaperTag",
    "PaperWorkState",
    "ReadingPlan",
    "ReadingPlanItem",
    "RecommendationCandidate",
    "RecommendationDecision",
    "RecommendationNarrationLease",
    "RecommendationRun",
    "ResearchConditions",
    "ResearchConditionsVersion",
    "ResearchContext",
    "ResearchContextDocument",
    "ResearchDirection",
    "SearchStrategyDraft",
    "SearchStrategyMeshTerm",
    "SearchStrategyTerm",
    "SearchStrategyVersion",
    "TaskRecord",
    "TopicStructuring",
    "TopicStructuringVersion",
    "TranslationTermOverride",
    "Writing",
    "WritingEvidenceReference",
    "ZoteroCollection",
    "ZoteroLibrary",
]
