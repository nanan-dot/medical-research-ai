"""NotesRAG 管道测试：编排、检索、保存/加载、目录索引。"""

from pathlib import Path

import pytest

from app.rag.embeddings import DummyEmbeddingClient
from app.rag.exceptions import NotesRAGError
from app.rag.notes_pipeline import NotesRAG, build_pipeline, index_notes_directory
from app.rag.schemas import SplitStrategy
from tests.rag.conftest import FakeEmbeddingClient, write_sample_note


@pytest.mark.asyncio
async def test_index_and_search_return_sources(tmp_path: Path):
    note = write_sample_note(
        tmp_path,
        name="note.md",
        body="# EGFR\nEGFR 耐药机制研究\n## 三代药\n奥希替尼对 T790M 有效\n",
    )
    rag = NotesRAG(
        index_dir=tmp_path / "index",
        embedding=FakeEmbeddingClient(dimension=8),
    )
    stats = await rag.index(tmp_path)
    assert stats.document_count == 1
    assert stats.chunk_count >= 2

    results = await rag.search("EGFR 耐药", top_k=2)
    assert results
    assert results[0].source_path == str(note)
    assert results[0].heading in {"EGFR", "三代药"}


@pytest.mark.asyncio
async def test_search_empty_query_is_rejected(tmp_path: Path):
    rag = NotesRAG(
        index_dir=tmp_path / "index",
        embedding=FakeEmbeddingClient(dimension=8),
    )
    await rag.index(tmp_path)
    with pytest.raises(NotesRAGError, match="must not be empty"):
        await rag.search("   ")


@pytest.mark.asyncio
async def test_search_without_index_is_explicit(tmp_path: Path):
    rag = NotesRAG(
        index_dir=tmp_path / "index",
        embedding=FakeEmbeddingClient(dimension=8),
    )
    with pytest.raises(NotesRAGError, match="no index is available"):
        await rag.search("query")


@pytest.mark.asyncio
async def test_index_empty_directory_is_ok(tmp_path: Path):
    rag = NotesRAG(
        index_dir=tmp_path / "index",
        embedding=FakeEmbeddingClient(dimension=8),
    )
    stats = await rag.index(tmp_path)
    assert stats.chunk_count == 0
    assert await rag.search("anything", top_k=1) == []


@pytest.mark.asyncio
async def test_index_missing_directory_is_explicit(tmp_path: Path):
    rag = NotesRAG(
        index_dir=tmp_path / "index",
        embedding=FakeEmbeddingClient(dimension=8),
    )
    with pytest.raises(NotesRAGError, match="does not exist"):
        await rag.index(tmp_path / "missing")


@pytest.mark.asyncio
async def test_save_and_load_round_trip(tmp_path: Path):
    write_sample_note(tmp_path, name="a.md", body="# A\nneedle content\n")
    rag = NotesRAG(
        index_dir=tmp_path / "index",
        embedding=FakeEmbeddingClient(dimension=8),
    )
    await rag.index(tmp_path)
    rag.save_index()

    reloaded = NotesRAG(index_dir=tmp_path / "index")
    reloaded.load_index()
    results = await reloaded.search("needle", top_k=1)
    assert results
    assert results[0].source_path.endswith("a.md")


def test_build_pipeline_returns_configured_rag(tmp_path: Path):
    rag = build_pipeline(
        embedding=FakeEmbeddingClient(dimension=8),
        index_dir=tmp_path / "pipeline-index",
        split_strategy=SplitStrategy(chunk_size=50),
    )
    assert rag.index_dir == tmp_path / "pipeline-index"


@pytest.mark.asyncio
async def test_index_notes_directory_uses_provided_store(tmp_path: Path):
    from app.rag.faiss_store import FaissIndexStore

    write_sample_note(tmp_path, name="b.md", body="# B\ncontent here\n")
    embedding = FakeEmbeddingClient(dimension=8)
    store = FaissIndexStore(
        tmp_path / "index", dimension=8, embedding_model=embedding.model_name
    )
    stats = await index_notes_directory(
        tmp_path,
        embedding=embedding,
        index_store=store,
    )
    assert stats.document_count == 1
    assert store.size == stats.chunk_count


@pytest.mark.asyncio
async def test_pipeline_with_dummy_embedding(tmp_path: Path):
    write_sample_note(tmp_path, name="c.md", body="# 标题\n正文内容\n")
    rag = NotesRAG(
        index_dir=tmp_path / "index",
        embedding=DummyEmbeddingClient(dimension=16),
    )
    stats = await rag.index(tmp_path)
    assert stats.dimension == 16
    results = await rag.search("标题", top_k=1)
    assert results
