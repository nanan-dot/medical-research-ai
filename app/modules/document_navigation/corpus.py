"""Map parsed documents, retrieval chunks, and navigation result evidence."""

import hashlib
import re
from dataclasses import dataclass

from app.modules.document.model import Document
from app.modules.document.parsers.schemas import ParsedDocument
from app.modules.document_navigation.conditions import match_navigation_conditions
from app.modules.document_navigation.schema import (
    DocumentNavigationResult,
    NavigationCondition,
    NavigationLocation,
)
from app.modules.document_upload.model import DocumentAsset
from app.modules.knowledge_source.model import KnowledgeSource
from app.rag.schemas import Chunk, RankedEvidence, RetrievalResult, to_ranked_evidence

_WHITESPACE = re.compile(r"\s+")
_EXCERPT_RADIUS = 180


@dataclass(frozen=True)
class SourceDocument:
    document: Document
    source: KnowledgeSource
    asset: DocumentAsset | None
    parsed: ParsedDocument


@dataclass(frozen=True)
class ChunkContext:
    document: SourceDocument
    page_number: int | None
    section: str | None


def make_navigation_chunks(
    documents: list[SourceDocument],
) -> tuple[list[Chunk], dict[str, ChunkContext]]:
    """Create traceable page and section chunks from parsed local documents."""

    chunks: list[Chunk] = []
    contexts: dict[str, ChunkContext] = {}
    for item in documents:
        entries: list[tuple[str, int | None, str | None]] = [
            (page.text, page.page_number, None)
            for page in item.parsed.pages
            if page.text.strip()
        ]
        entries += [
            (section.text, None, section.heading)
            for section in item.parsed.sections
            if section.text.strip()
        ]
        if not entries and item.parsed.text.strip():
            entries = [(item.parsed.text, None, None)]
        for index, (text, page_number, section) in enumerate(entries):
            chunk_id = f"document:{item.document.id}:{index}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=str(item.document.id),
                    heading=section or "",
                    text=text,
                    source_path=item.document.file_path,
                )
            )
            contexts[chunk_id] = ChunkContext(item, page_number, section)
    return chunks, contexts


def format_navigation_results(
    results: list[RetrievalResult],
    contexts: dict[str, ChunkContext],
    conditions: list[NavigationCondition],
    rerank_scores: dict[str, float],
    limit: int,
) -> tuple[list[DocumentNavigationResult], set[str]]:
    """Deduplicate identical source text and preserve its evidence identity."""

    navigation_results: list[DocumentNavigationResult] = []
    selected_chunk_ids: set[str] = set()
    seen: set[tuple[int, str]] = set()
    for result in results:
        context = contexts.get(result.chunk_id)
        if context is None:
            continue
        identity = (
            context.document.document.id,
            _WHITESPACE.sub(" ", result.text).strip(),
        )
        if identity in seen:
            continue
        seen.add(identity)
        item = _to_navigation_result(result, context, conditions)
        item.rerank_score = rerank_scores.get(result.chunk_id)
        navigation_results.append(item)
        selected_chunk_ids.add(result.chunk_id)
        if len(navigation_results) >= limit:
            break
    return navigation_results, selected_chunk_ids


def to_ranked_evidence_list(
    results: list[RetrievalResult],
    contexts: dict[str, ChunkContext],
    index_version: str,
) -> list[RankedEvidence]:
    """Convert retrieval candidates to the shared auditable evidence contract."""

    evidence: list[RankedEvidence] = []
    for rank, result in enumerate(results, start=1):
        context = contexts.get(result.chunk_id)
        if context is None:
            continue
        evidence.append(
            to_ranked_evidence(
                result.model_copy(update={"rank": rank}),
                document_id=str(context.document.document.id),
                section=context.section,
                page_number=context.page_number,
                index_version=index_version,
            )
        )
    return evidence


def scope_index_version(chunks: list[Chunk]) -> str:
    """Fingerprint the exact scoped content represented by an in-memory index."""

    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(chunk.model_dump_json().encode("utf-8"))
    return digest.hexdigest()


def _to_navigation_result(
    result: RetrievalResult,
    context: ChunkContext,
    requested: list[NavigationCondition],
) -> DocumentNavigationResult:
    evidence = to_ranked_evidence(
        result,
        document_id=str(context.document.document.id),
        section=context.section,
        page_number=context.page_number,
    )
    item = context.document
    filename = (
        item.asset.original_filename
        if item.asset
        else item.document.file_path.replace("\\", "/").rsplit("/", 1)[-1]
    )
    score = (
        result.fused_score
        if result.retriever_name == "hybrid"
        else result.raw_score
    )
    return DocumentNavigationResult(
        document_id=item.document.id,
        title=item.parsed.title or filename,
        filename=filename,
        knowledge_source_id=item.source.id,
        knowledge_source_name=item.source.name,
        relative_path=evidence.source_path,
        match_reason=f"{result.retriever_name} 召回的本地原文块",
        location=NavigationLocation(
            page_number=evidence.page_number, section=evidence.section
        ),
        excerpt=_excerpt(evidence.text_original),
        retrieval_score=score,
        condition_status=requested,
        condition_matches=match_navigation_conditions(
            requested, item.parsed, result.text
        ),
    )


def _excerpt(text: str) -> str:
    compact = _WHITESPACE.sub(" ", text).strip()
    return compact[:_EXCERPT_RADIUS] + (
        "…" if len(compact) > _EXCERPT_RADIUS else ""
    )
