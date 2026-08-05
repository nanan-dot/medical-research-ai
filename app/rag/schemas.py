"""Mini-RAG 基线（R2-WP09）的公开数据结构。"""

from typing import Literal

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
    score: float
