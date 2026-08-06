"""将 WP09 的 FAISS 存储适配为文本检索共同接口。"""

from collections.abc import Callable

from app.rag.faiss_store import FaissIndexStore
from app.rag.schemas import RetrievalResult

QueryVectorProvider = Callable[[str], list[float]]


class VectorRetriever:
    """通过注入的查询嵌入函数把 FAISS 检索器适配为文本检索器。"""

    def __init__(self, *, index_store: FaissIndexStore, embed_query: QueryVectorProvider) -> None:
        self._index_store = index_store
        self._embed_query = embed_query

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """生成查询向量并复用 WP09 FAISS Top-K 与元数据回查。"""
        if top_k <= 0:
            return []
        return self._index_store.search(self._embed_query(query), top_k=top_k)
