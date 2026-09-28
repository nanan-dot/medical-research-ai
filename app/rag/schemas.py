"""Mini-RAG 基线（R2-WP09）的公开数据结构。"""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.rag.exceptions import NotesRAGError

EMPTY_TEXT_MAX_LENGTH = 100


class EmptyChunkError(NotesRAGError):
    """切片文本为空（不可建立无内容分块）。"""

    code = "empty_chunk"


class SplitStrategy(BaseModel):
    """切片策略配置。

    设计说明：标题层级与固定长度回退是两个正交维度——
    先用标题切出语义块，仅当块超长时才按固定长度回退切片（重叠可选）。
    """

    mode: Literal["heading", "fixed_length"] = "heading"
    chunk_size: int = Field(default=1000, gt=0)
    overlap: int = Field(default=100, ge=0)


class Chunk(BaseModel):
    """一个可检索的分块。

    - ``heading``：所属标题（无标题时为空串）；
    - ``vector_id``：写入 FAISS 后回填的整数 ID（与 ``metadata.json`` 双向映射）。
    """

    chunk_id: str
    document_id: str
    heading: str = ""
    text: str = Field(min_length=1)
    source_path: str = ""
    vector_id: int | None = Field(default=None)

    def validate_text(self) -> None:
        """丢弃纯空白文本：空块无法检索也没有引用意义。"""
        if not self.text.strip():
            raise EmptyChunkError(
                "chunk text is empty; skip empty sections or trim whitespace"
            )


class VectorChunkRecord(BaseModel):
    """FAISS 按 vector_id 回查的元数据记录（存于独立 JSON，非 FAISS 内部）。"""

    vector_id: int
    chunk_id: str
    document_id: str
    heading: str
    text: str
    source_path: str


class IndexMetadata(BaseModel):
    """索引文件的描述性元数据（不存向量内容）。"""

    embedding_model: str
    dimension: int = Field(gt=0)
    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)


class IndexStats(BaseModel):
    """建索引后返回的统计信息。"""

    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    dimension: int = Field(gt=0)


class RetrievalResult(BaseModel):
    """一条检索结果，携带可解释引用信息（来源路径 + 标题）。"""

    text: str
    source_path: str
    heading: str
    # ``score`` 保留给 WP09 调用方兼容；新代码应读取可追溯的 raw/fused 字段。
    score: float | None = None
    chunk_id: str = ""
    retriever_name: Literal["vector", "bm25", "hybrid"] = "vector"
    rank: int = Field(default=1, ge=1)
    raw_score: float | None = None
    fused_score: float | None = None
    contributions: list["RetrievalContribution"] = Field(default_factory=list)


class RetrievalContribution(BaseModel):
    """单一路检索对融合结果的可追溯贡献。"""

    retriever_name: Literal["vector", "bm25"]
    rank: int = Field(ge=1)
    raw_score: float


class Constraint(BaseModel):
    field: str
    value: str
    status: Literal["required", "preferred", "excluded"] = "preferred"


ConstraintStatus = Literal["satisfied", "unsatisfied", "not_applicable", "unknown"]


class QueryPlan(BaseModel):
    query: str
    constraints: list[Constraint] = Field(default_factory=list)
    profile: str = "local_evidence"


class RetrievalCandidate(BaseModel):
    document_id: str
    chunk_id: str
    source_path: str
    heading: str = ""
    section: str | None = None
    page_number: int | None = None
    text_original: str
    index_version: str | None = None


class RankedEvidence(RetrievalCandidate):
    rank: int = Field(ge=1)
    score: float | None = None
    contributions: list[RetrievalContribution] = Field(default_factory=list)
    role: Literal["direct", "context", "comparative", "conflicting"] = "context"


class NumericFact(BaseModel):
    metric: str
    value: str
    unit: str
    population: str
    source_chunk_id: str
    verified: bool = False


class EvidenceConflict(BaseModel):
    metric: str
    population: str
    source_chunk_ids: list[str] = Field(default_factory=list)


class EvidenceSet(BaseModel):
    evidence: list[RankedEvidence] = Field(default_factory=list)
    numeric_facts: list[NumericFact] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    status: Literal["ready", "insufficient_evidence"] = "ready"


class GroundedClaim(BaseModel):
    claim: str
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    is_numeric: bool = False
    numeric_fact_ids: list[str] = Field(default_factory=list)


class GroundedCitation(BaseModel):
    citation_id: str
    document_id: str
    database_document_id: int | None = Field(default=None, gt=0)
    chunk_id: str
    source_path: str
    page_number: int | None = None


class GroundedAnswer(BaseModel):
    answer: str
    claims: list[GroundedClaim] = Field(default_factory=list)
    citations: list[GroundedCitation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_status: Literal["ready", "insufficient_evidence", "system_failure"] = "ready"
    trace_id: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    fallback: bool = False


class RetrievalTrace(BaseModel):
    """可版本化的检索审计记录；内容持久化策略由 ``TraceStore`` 执行。"""

    schema_version: Literal["rag-trace-v1"] = "rag-trace-v1"
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    query_original: str | None = None
    query_plan: QueryPlan
    profile: str = "local_evidence"
    rerank_status: Literal["disabled", "applied", "fallback", "empty"] | None = None
    rerank_reason_code: Literal[
        "disabled",
        "applied",
        "no_candidates",
        "model_unavailable",
        "model_busy",
        "timeout",
        "inference_error",
    ] | None = None
    filters: dict[str, object] = Field(default_factory=dict)
    retriever_versions: dict[str, str] = Field(default_factory=dict)
    dense_candidates: list[RankedEvidence] = Field(default_factory=list)
    sparse_candidates: list[RankedEvidence] = Field(default_factory=list)
    rrf_candidates: list[RankedEvidence] = Field(default_factory=list)
    reranked_candidates: list[RankedEvidence] = Field(default_factory=list)
    selected_evidence: EvidenceSet = Field(default_factory=EvidenceSet)
    rejected_evidence: list[RankedEvidence] = Field(default_factory=list)
    fallbacks: list[str] = Field(default_factory=list)
    latency_by_stage: dict[str, int] = Field(default_factory=dict)
    answer: GroundedAnswer | None = None
    citations: list[GroundedCitation] = Field(default_factory=list)
    prompt_version: str | None = None
    model_version: str | None = None
    index_version: str | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # WP3 的旧字段保留，避免已有调用方在协议升级时失效。
    candidates: list[RetrievalCandidate] = Field(default_factory=list)
    evidence: EvidenceSet = Field(default_factory=EvidenceSet)


def to_ranked_evidence(
    result: RetrievalResult,
    *,
    document_id: str,
    section: str | None = None,
    page_number: int | None = None,
    index_version: str | None = None,
) -> RankedEvidence:
    """Adapt legacy retrieval output at a boundary without losing provenance."""
    return RankedEvidence(
        document_id=document_id,
        chunk_id=result.chunk_id,
        source_path=result.source_path,
        heading=result.heading,
        section=section,
        page_number=page_number,
        text_original=result.text,
        index_version=index_version,
        rank=result.rank,
        score=result.fused_score if result.fused_score is not None else result.raw_score,
        contributions=result.contributions,
    )
