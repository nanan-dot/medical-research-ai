"""Mini-RAG 基线（R2-WP09）的结构化异常。"""

from app.common.exceptions import AppError


class NotesRAGError(AppError):
    """Mini-RAG 基线的基础异常。"""

    code = "notes_rag_error"


class GroundedGenerationError(NotesRAGError):
    """A generator adapter failed without exposing model internals."""


class InvalidGeneratedAnswerError(GroundedGenerationError):
    """A generator returned an application-invalid grounded response."""


class EmbeddingDimensionMismatchError(NotesRAGError):
    """已保存索引的向量维度与当前 Embedding 配置不一致。

    触发原因：换用了不同维度的模型（如 nomic-embed-text 384 维换到其他模型）。
    处理策略：向调用方明确提示"重建索引"，而不是静默加载不匹配的向量。
    """

    code = "embedding_dimension_mismatch"


class IndexCorruptError(NotesRAGError):
    """向量索引文件损坏或不可解析。

    处理策略：显式报错并给出重建指引，不静默吞掉（对齐 CODE_STANDARDS 禁空捕获）。
    """

    code = "index_corrupt"


class IndexNotLoadedError(NotesRAGError):
    """检索时索引尚未加载或未建立。"""

    code = "index_not_loaded"
