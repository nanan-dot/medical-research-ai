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
    IndexStats,
    RetrievalContribution,
    RetrievalResult,
    SplitStrategy,
)
from app.rag.splitter import split_markdown_document
from app.rag.vector_retriever import VectorRetriever

__all__ = [
    "RRF_K",
    "BM25Store",
    "Chunk",
    "DummyEmbeddingClient",
    "EmbeddingClient",
    "EmbeddingDimensionMismatchError",
    "EmbeddingError",
    "FaissIndexStore",
    "HybridRetriever",
    "IndexCorruptError",
    "IndexMetadata",
    "IndexNotLoadedError",
    "IndexStats",
    "NotesRAG",
    "NotesRAGError",
    "OllamaEmbeddingClient",
    "RetrievalContribution",
    "RetrievalResult",
    "SplitStrategy",
    "TextRetriever",
    "VectorChunkRecord",
    "VectorRetriever",
    "build_pipeline",
    "create_embedding_client",
    "fuse_ranked_results",
    "index_notes_directory",
    "read_index_metadata",
    "split_markdown_document",
    "tokenize_medical_text",
]
