"""Aggregate only indexed local documents into an explainable RAG search request."""

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.document.model import Document
from app.modules.document.parsers.schemas import ParsedDocument
from app.modules.document_upload.model import DocumentAsset
from app.modules.document_navigation.schema import (
    DocumentNavigationRequest, DocumentNavigationResponse, DocumentNavigationResult,
    NavigationCondition, NavigationLocation, NavigationStrategy, VerificationStatus,
)
from app.modules.knowledge_source.model import KnowledgeSource
from app.rag.bm25_store import BM25Store
from app.rag.embeddings import EmbeddingError, create_embedding_client
from app.rag.faiss_store import FaissIndexStore
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.schemas import Chunk, RetrievalResult
from app.rag.vector_retriever import VectorRetriever

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_RCT = re.compile(r"随机[对照化]试验|随机对照|randomi[sz]ed controlled trial|\bRCT\b", re.I)
_WHITESPACE = re.compile(r"\s+")
_EXCERPT_RADIUS = 180


@dataclass(frozen=True)
class _SourceDocument:
    document: Document
    source: KnowledgeSource
    asset: DocumentAsset | None
    parsed: ParsedDocument


@dataclass(frozen=True)
class _ChunkContext:
    document: _SourceDocument
    page_number: int | None
    section: str | None


class DocumentNavigationService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def search(self, request: DocumentNavigationRequest) -> DocumentNavigationResponse:
        query = request.query.strip()
        documents = await self._load_documents(request)
        chunks, contexts = _make_chunks(documents)
        requested_conditions = _requested_conditions(query)
        if not chunks:
            return _empty_response(request, query, len(documents), requested_conditions)

        bm25 = BM25Store()
        bm25.build(chunks)
        results, strategy, fallback_reason = await self._retrieve(query, chunks, bm25, request.limit)
        navigation_results = [
            _to_navigation_result(result, contexts[result.chunk_id], requested_conditions)
            for result in results
            if result.chunk_id in contexts
        ]
        return DocumentNavigationResponse(
            query=query, knowledge_source_id=request.knowledge_source_id,
            indexed_only=request.indexed_only, searchable_document_count=len(documents),
            strategy=strategy, fallback_reason=fallback_reason,
            conditions=requested_conditions, results=navigation_results,
        )

    async def _load_documents(self, request: DocumentNavigationRequest) -> list[_SourceDocument]:
        statement = (
            select(Document, KnowledgeSource, DocumentAsset)
            .join(KnowledgeSource, Document.knowledge_source_id == KnowledgeSource.id)
            .outerjoin(DocumentAsset, DocumentAsset.document_id == Document.id)
            .where(Document.parse_status == "succeeded", Document.parsed_content.is_not(None), KnowledgeSource.enabled.is_(True))
        )
        # 全库 RAG 没有安全的跨 PaperQA2 索引能力，因此本导航始终只接受已索引资料。
        statement = statement.where(Document.index_status == "succeeded", Document.paperqa_index_key.is_not(None), Document.paperqa_index_key != "")
        if request.knowledge_source_id is not None:
            statement = statement.where(Document.knowledge_source_id == request.knowledge_source_id)
        rows = (await self._session.execute(statement)).all()
        documents: list[_SourceDocument] = []
        for document, source, asset in rows:
            try:
                parsed = ParsedDocument.model_validate_json(document.parsed_content)
            except ValueError:
                continue
            documents.append(_SourceDocument(document, source, asset, parsed))
        return documents

    async def _retrieve(self, query: str, chunks: list[Chunk], bm25: BM25Store, limit: int) -> tuple[list[RetrievalResult], NavigationStrategy, str | None]:
        if settings.EMBEDDING_PROVIDER != "ollama":
            return _matched_bm25(bm25, query, limit), NavigationStrategy.BM25, "本机语义向量未启用，已使用可解释的 BM25 词法检索。"
        try:
            embedding = create_embedding_client(provider="ollama", base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_EMBEDDING_MODEL, dimension=settings.EMBEDDING_DIMENSION)
            vectors = await embedding.embed([chunk.text for chunk in chunks])
            store = FaissIndexStore(Path("data/document_navigation_runtime"), dimension=embedding.dimension, embedding_model=embedding.model_name)
            store.build(chunks, vectors)
            query_vector = (await embedding.embed([query]))[0]
            vector = VectorRetriever(index_store=store, embed_query=lambda _: query_vector)
            # HybridRetriever 使用现有 RRF 融合；向量和 BM25 都来自本次筛选的真实本地解析块。
            results = await asyncio.to_thread(HybridRetriever(vector_retriever=vector, bm25_retriever=bm25).search, query, limit)
            return results, NavigationStrategy.HYBRID, None
        except (EmbeddingError, RuntimeError, ValueError, OSError) as error:
            return _matched_bm25(bm25, query, limit), NavigationStrategy.BM25, f"本机语义向量不可用，已降级为 BM25：{str(error)}"


def _make_chunks(documents: list[_SourceDocument]) -> tuple[list[Chunk], dict[str, _ChunkContext]]:
    chunks: list[Chunk] = []
    contexts: dict[str, _ChunkContext] = {}
    for item in documents:
        entries = [(page.text, page.page_number, None) for page in item.parsed.pages if page.text.strip()]
        entries += [(section.text, None, section.heading) for section in item.parsed.sections if section.text.strip()]
        if not entries and item.parsed.text.strip(): entries = [(item.parsed.text, None, None)]
        for index, (text, page_number, section) in enumerate(entries):
            chunk_id = f"document:{item.document.id}:{index}"
            chunks.append(Chunk(chunk_id=chunk_id, document_id=str(item.document.id), heading=section or "", text=text, source_path=item.document.file_path))
            contexts[chunk_id] = _ChunkContext(item, page_number, section)
    return chunks, contexts


def _matched_bm25(store: BM25Store, query: str, limit: int) -> list[RetrievalResult]:
    """BM25Store 为通用组件保留零分排序；导航 API 的“未命中”必须是空结果。"""
    return [result for result in store.search(query, limit) if (result.raw_score or 0) > 0]


def _requested_conditions(query: str) -> list[NavigationCondition]:
    conditions: list[NavigationCondition] = []
    if "近三年" in query:
        conditions.append(NavigationCondition(label="近三年", status=VerificationStatus.UNVERIFIED, reason="仅当命中文本含可验证年份时才会标记为已验证。"))
    if _RCT.search(query):
        conditions.append(NavigationCondition(label="随机对照试验", status=VerificationStatus.UNVERIFIED, reason="仅当命中文本明确出现试验类型表述时才会标记为已验证。"))
    return conditions


def _to_navigation_result(result: RetrievalResult, context: _ChunkContext, requested: list[NavigationCondition]) -> DocumentNavigationResult:
    text = result.text
    conditions = [_verify_condition(condition, text) for condition in requested]
    item = context.document
    filename = item.asset.original_filename if item.asset else item.document.file_path.rsplit("/", 1)[-1]
    score = result.fused_score if result.retriever_name == "hybrid" else result.raw_score
    return DocumentNavigationResult(document_id=item.document.id, title=item.parsed.title or filename, filename=filename, knowledge_source_id=item.source.id, knowledge_source_name=item.source.name, relative_path=item.document.file_path, match_reason=f"{result.retriever_name} 召回的本地原文块", location=NavigationLocation(page_number=context.page_number, section=context.section), excerpt=_excerpt(text), retrieval_score=score, condition_status=conditions)


def _verify_condition(condition: NavigationCondition, text: str) -> NavigationCondition:
    if condition.label == "随机对照试验":
        verified = bool(_RCT.search(text))
    else:
        years = [int(value) for value in _YEAR.findall(text)]
        verified = any(year >= 2023 for year in years)
    return condition.model_copy(update={"status": VerificationStatus.VERIFIED if verified else VerificationStatus.UNVERIFIED, "reason": "命中原文可验证该条件。" if verified else "本次命中原文未提供可验证依据，仅表示检索相关。"})


def _excerpt(text: str) -> str:
    compact = _WHITESPACE.sub(" ", text).strip()
    return compact[:_EXCERPT_RADIUS] + ("…" if len(compact) > _EXCERPT_RADIUS else "")


def _empty_response(request: DocumentNavigationRequest, query: str, count: int, conditions: list[NavigationCondition]) -> DocumentNavigationResponse:
    return DocumentNavigationResponse(query=query, knowledge_source_id=request.knowledge_source_id, indexed_only=request.indexed_only, searchable_document_count=count, strategy=NavigationStrategy.BM25, fallback_reason="当前范围没有可用于跨文档检索的已解析且已索引资料。", conditions=conditions, results=[])
