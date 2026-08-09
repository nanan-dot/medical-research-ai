"""Mini-RAG 笔记管道：解析→切片→embed→建索引→检索。

设计意图：
- ``index_notes_directory`` 是底层编排函数（纯逻辑、可注入替身），负责
  读取目录 → 切片 → 嵌入 → 建索引；
- ``NotesRAG`` 是面向调用方的门面：``index`` / ``search`` / ``save_index`` /
  ``load_index`` 的 Python API，同时承载索引目录与 Embedding 客户端的生命周期；
- ``build_pipeline`` 提供从 Embedding 客户端到 NotesRAG 的组装入口。

实现顺序说明：**先切片再 embed**。Ollama 这类懒加载客户端的维度要等首次
调用后才知道，因此先把向量全部产出，再按真实维度构建 store，避免维度不一致。
"""

import logging
import os
from pathlib import Path

from app.rag.embeddings import EmbeddingClient, create_embedding_client
from app.rag.exceptions import NotesRAGError
from app.rag.faiss_store import FaissIndexStore, read_index_metadata
from app.rag.schemas import Chunk, IndexStats, RetrievalResult, SplitStrategy
from app.rag.splitter import split_markdown_document

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
# 默认索引目录：与 Settings.NOTES_INDEX_DIR 对齐，调用方可覆盖
DEFAULT_INDEX_DIR = Path("data/notes_index")


async def index_notes_directory(
    notes_dir: Path,
    *,
    embedding: EmbeddingClient,
    index_store: FaissIndexStore,
    strategy: SplitStrategy | None = None,
) -> IndexStats:
    """读取目录下所有 ``.md`` 文件，切片后嵌入并写入索引 store。

    单文件解析失败只跳过并记录警告，不中断整个目录索引；
    空目录仍会建立空索引（后续可增量 add）。
    """
    if not notes_dir.is_dir():
        raise NotesRAGError(f"notes directory does not exist: {notes_dir}")

    all_chunks: list[Chunk] = []
    for path in sorted(notes_dir.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8-sig", errors="strict")
        except (OSError, UnicodeDecodeError) as error:
            logger.warning("skip unreadable note %s: %s", path, error)
            continue
        chunks = split_markdown_document(
            content,
            document_id=path.stem,
            source_path=str(path),
            strategy=strategy,
        )
        all_chunks.extend(chunks)

    vectors = await embedding.embed([chunk.text for chunk in all_chunks])
    index_store.build(all_chunks, vectors)
    return IndexStats(
        document_count=len({chunk.document_id for chunk in all_chunks}),
        chunk_count=len(all_chunks),
        dimension=embedding.dimension,
    )


class NotesRAG:
    """面向调用方的 Mini-RAG 门面：索引 + 检索 + 索引持久化。

    使用示例（Python API，非 HTTP）：

    .. code-block:: python

        rag = NotesRAG(index_dir=Path("data/notes_index"))
        stats = await rag.index(Path("experiments/minirag/notes"))
        results = await rag.search("什么是 EGFR 耐药机制？")
        await rag.save_index()
    """

    def __init__(
        self,
        *,
        index_dir: Path = DEFAULT_INDEX_DIR,
        embedding: EmbeddingClient | None = None,
        split_strategy: SplitStrategy | None = None,
    ) -> None:
        self.index_dir = Path(index_dir)
        self._embedding = embedding
        self._split_strategy = split_strategy or SplitStrategy()
        self._store: FaissIndexStore | None = None

    async def index(self, notes_dir: Path) -> IndexStats:
        """对目录下的 Markdown 笔记建索引（进程内重建）。

        先切片再 embed，得到真实向量维度后构建 store（见模块 docstring）。
        """
        if not notes_dir.is_dir():
            raise NotesRAGError(f"notes directory does not exist: {notes_dir}")

        all_chunks: list[Chunk] = []
        for path in sorted(notes_dir.glob("*.md")):
            try:
                content = path.read_text(encoding="utf-8-sig", errors="strict")
            except (OSError, UnicodeDecodeError) as error:
                logger.warning("skip unreadable note %s: %s", path, error)
                continue
            chunks = split_markdown_document(
                content,
                document_id=path.stem,
                source_path=str(path),
                strategy=self._split_strategy,
            )
            all_chunks.extend(chunks)

        embedding = self._require_embedding()
        vectors = await embedding.embed([chunk.text for chunk in all_chunks])
        store = self._make_store()
        store.build(all_chunks, vectors)
        self._store = store
        return IndexStats(
            document_count=len({chunk.document_id for chunk in all_chunks}),
            chunk_count=len(all_chunks),
            dimension=embedding.dimension,
        )

    async def search(
        self, query: str, top_k: int = DEFAULT_TOP_K
    ) -> list[RetrievalResult]:
        """对查询文本嵌入后做 Top-K 检索，返回带来源的引用结果。"""
        if not query.strip():
            raise NotesRAGError("search query must not be empty")
        embedding = self._require_embedding()
        store = self._require_store()
        query_vector = await embedding.embed([query])
        return store.search(query_vector[0], top_k=top_k)

    def save_index(self, index_dir: Path | None = None) -> Path:
        store = self._require_store()
        return store.save(index_dir)

    def load_index(self, index_dir: Path | None = None) -> None:
        """加载索引；维度不匹配会先由 manifest 校验抛错提示重建。"""
        load_dir = Path(index_dir) if index_dir is not None else self.index_dir
        embedding_model, stored_dimension = read_index_metadata(load_dir)
        store = FaissIndexStore(
            load_dir,
            dimension=stored_dimension,
            embedding_model=embedding_model,
        )
        store.load(load_dir)
        self._store = store
        # 恢复 embedding 客户端：构造时未注入时，按索引元数据重建默认客户端。
        # 这样"重启后加载索引再检索"的流程无需调用方额外传 embedding。
        if self._embedding is None:
            self._embedding = create_embedding_client(
                provider=os.getenv("EMBEDDING_PROVIDER", "dummy"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
                dimension=stored_dimension,
            )

    def _make_store(self) -> FaissIndexStore:
        if self._embedding is None:
            raise NotesRAGError("an embedding client is required before indexing")
        return FaissIndexStore(
            self.index_dir,
            dimension=self._embedding.dimension,
            embedding_model=self._embedding.model_name,
        )

    def _require_embedding(self) -> EmbeddingClient:
        """返回注入的 embedding 客户端；缺失时抛错（mypy 收窄 Optional）。"""
        if self._embedding is None:
            raise NotesRAGError(
                "an embedding client is required; inject one or load an index"
            )
        return self._embedding

    def _require_store(self) -> FaissIndexStore:
        """返回已加载的索引存储；未加载时抛错（mypy 收窄 Optional）。"""
        if self._store is None:
            raise NotesRAGError(
                "no index is available; call index() or load_index() first"
            )
        return self._store


def build_pipeline(
    *,
    embedding: EmbeddingClient,
    index_dir: Path = DEFAULT_INDEX_DIR,
    split_strategy: SplitStrategy | None = None,
) -> NotesRAG:
    """按给定 Embedding 客户端组装一个 NotesRAG 实例。"""
    return NotesRAG(
        index_dir=index_dir,
        embedding=embedding,
        split_strategy=split_strategy,
    )
