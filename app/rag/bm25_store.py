"""基于 WP09 Chunk 的确定性 BM25 词法索引。"""

import math
import re

from app.rag.schemas import Chunk, RetrievalResult

BM25_K1 = 1.5
BM25_B = 0.75
_ALPHANUMERIC_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")
_CHINESE_RUN_PATTERN = re.compile(r"[\u4e00-\u9fff]+")


def tokenize_medical_text(text: str) -> list[str]:
    """为医学精确词保留字母数字 token，并以中文二元组处理未登录词。"""
    normalized = text.casefold()
    tokens = _ALPHANUMERIC_TOKEN_PATTERN.findall(normalized)
    for chinese_run in _CHINESE_RUN_PATTERN.findall(normalized):
        if len(chinese_run) == 1:
            tokens.append(chinese_run)
            continue
        tokens.extend(chinese_run[index : index + 2] for index in range(len(chinese_run) - 1))
    return tokens


class BM25Store:
    """内存 BM25 索引；增量添加后整体重算 IDF，避免旧文档权重失真。"""

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._document_tokens: list[list[str]] = []
        self._document_frequencies: dict[str, int] = {}
        self._average_document_length = 0.0

    @property
    def size(self) -> int:
        """返回已索引分块数量。"""
        return len(self._chunks)

    def build(self, chunks: list[Chunk]) -> None:
        """从完整分块集合重建索引。"""
        self._chunks = list(chunks)
        self._recalculate_statistics()

    def add(self, chunks: list[Chunk]) -> None:
        """追加分块后重算全局统计量，保证 BM25 IDF 与平均长度一致。"""
        self._chunks.extend(chunks)
        self._recalculate_statistics()

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """按 BM25 分数返回词法 Top-K，非正 K 或空索引返回空。"""
        if top_k <= 0 or not self._chunks:
            return []
        query_tokens = tokenize_medical_text(query)
        if not query_tokens:
            return []
        ranked_indices = sorted(
            range(len(self._chunks)),
            key=lambda index: (-self._score_document(index, query_tokens), index),
        )
        results: list[RetrievalResult] = []
        for index in ranked_indices[:top_k]:
            chunk = self._chunks[index]
            score = self._score_document(index, query_tokens)
            results.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    source_path=chunk.source_path,
                    heading=chunk.heading,
                    score=score,
                    retriever_name="bm25",
                    rank=len(results) + 1,
                    raw_score=score,
                )
            )
        return results

    def _recalculate_statistics(self) -> None:
        self._document_tokens = [tokenize_medical_text(chunk.text) for chunk in self._chunks]
        self._document_frequencies = {}
        for tokens in self._document_tokens:
            for token in set(tokens):
                self._document_frequencies[token] = self._document_frequencies.get(token, 0) + 1
        total_token_count = sum(len(tokens) for tokens in self._document_tokens)
        self._average_document_length = (
            total_token_count / len(self._document_tokens) if self._document_tokens else 0.0
        )

    def _score_document(self, index: int, query_tokens: list[str]) -> float:
        tokens = self._document_tokens[index]
        if not tokens or self._average_document_length == 0:
            return 0.0
        term_frequencies: dict[str, int] = {}
        for token in tokens:
            term_frequencies[token] = term_frequencies.get(token, 0) + 1
        document_length = len(tokens)
        total_documents = len(self._document_tokens)
        score = 0.0
        for token in set(query_tokens):
            frequency = term_frequencies.get(token, 0)
            if frequency == 0:
                continue
            document_frequency = self._document_frequencies.get(token, 0)
            inverse_document_frequency = math.log(
                1 + (total_documents - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            denominator = frequency + BM25_K1 * (
                1 - BM25_B + BM25_B * document_length / self._average_document_length
            )
            score += inverse_document_frequency * frequency * (BM25_K1 + 1) / denominator
        return score
