"""Mini-RAG 基线（R2-WP09）——本地优先的 Markdown 笔记检索。

设计边界（对齐 docs/SKILLS_FUSION_MAP.md 与 R2-WP09 限制）：
- 只处理 Markdown 笔记，不做高级多向量与 Agent；
- Embedding 本地优先（Ollama），dummy 仅开发兜底，禁止默认调用云端；
- 检索结果携带来源路径与标题，可解释引用（反幻觉协议延伸）。
"""

from app.rag.bm25_store import BM25Store, tokenize_medical_text
from app.rag.embeddings import (
    DummyEmbeddingClient,
    EmbeddingClient,
    EmbeddingError,
    OllamaEmbeddingClient,
    create_embedding_client,
)
from app.rag.evidence_builder import build_evidence_set
from app.rag.exceptions import (
    EmbeddingDimensionMismatchError,
    IndexCorruptError,
    IndexNotLoadedError,
    NotesRAGError,
)
from app.rag.faiss_store import (
    FaissIndexStore,
    IndexMetadata,
    VectorChunkRecord,
    read_index_metadata,
)
from app.rag.hybrid_retriever import HybridRetriever, TextRetriever
from app.rag.notes_pipeline import NotesRAG, build_pipeline, index_notes_directory
from app.rag.rrf import RRF_K, fuse_ranked_results
from app.rag.schemas import (
    Chunk,
    Constraint,
    EvidenceSet,
    GroundedAnswer,
    GroundedClaim,
    IndexStats,
    QueryPlan,
    RankedEvidence,
    RetrievalCandidate,
    RetrievalContribution,
    RetrievalResult,
    RetrievalTrace,
    SplitStrategy,
    to_ranked_evidence,
)
from app.rag.shadow_release import (
    ReleaseDecision,
    ReleaseEvidence,
    ShadowComparison,
    ShadowComparisonRunner,
    StrategyOutcome,
    evaluate_release_gate,
    resolve_user_visible_mode,
)
from app.rag.splitter import split_markdown_document
from app.rag.trace import (
    TracePolicy,
    TraceStore,
    replay_candidate_ids,
    trace_policy_from_settings,
    trace_store_from_settings,
)
from app.rag.transformers_reranker import (
    LocalModelUnavailableError,
    TransformersCrossEncoderScorer,
    create_bge_reranker,
)
from app.rag.vector_retriever import VectorRetriever

__all__ = [
    "RRF_K",
    "BM25Store",
    "Chunk",
    "Constraint",
    "DummyEmbeddingClient",
    "EmbeddingClient",
    "EmbeddingDimensionMismatchError",
    "EmbeddingError",
    "EvidenceSet",
    "FaissIndexStore",
    "GroundedAnswer",
    "GroundedClaim",
    "HybridRetriever",
    "IndexCorruptError",
    "IndexMetadata",
    "IndexNotLoadedError",
    "IndexStats",
    "LocalModelUnavailableError",
    "NotesRAG",
    "NotesRAGError",
    "OllamaEmbeddingClient",
    "QueryPlan",
    "RankedEvidence",
    "ReleaseDecision",
    "ReleaseEvidence",
    "RetrievalCandidate",
    "RetrievalContribution",
    "RetrievalResult",
    "RetrievalTrace",
    "ShadowComparison",
    "ShadowComparisonRunner",
    "SplitStrategy",
    "StrategyOutcome",
    "TextRetriever",
    "TracePolicy",
    "TraceStore",
    "TransformersCrossEncoderScorer",
    "VectorChunkRecord",
    "VectorRetriever",
    "build_evidence_set",
    "build_pipeline",
    "create_bge_reranker",
    "create_embedding_client",
    "evaluate_release_gate",
    "fuse_ranked_results",
    "index_notes_directory",
    "read_index_metadata",
    "replay_candidate_ids",
    "resolve_user_visible_mode",
    "split_markdown_document",
    "to_ranked_evidence",
    "tokenize_medical_text",
    "trace_policy_from_settings",
    "trace_store_from_settings",
]
