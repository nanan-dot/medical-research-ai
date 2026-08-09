"""FaissIndexStore 测试：构建/保存/加载 round-trip、Top-K、来源映射、维度校验。"""

import json
from pathlib import Path

import pytest

from app.rag.exceptions import (
    EmbeddingDimensionMismatchError,
    IndexCorruptError,
    IndexNotLoadedError,
    NotesRAGError,
)
from app.rag.faiss_store import (
    METADATA_FILE,
    VECTOR_IDS_FILE,
    VECTORS_FILE,
    FaissIndexStore,
    read_index_metadata,
)
from tests.rag.conftest import make_chunk

DIMENSION = 4


def _vectors(count: int, dimension: int = DIMENSION) -> list[list[float]]:
    return [
        [float(index) + float(row) for index in range(dimension)]
        for row in range(count)
    ]


def _store(tmp_path: Path) -> FaissIndexStore:
    return FaissIndexStore(
        tmp_path / "index",
        dimension=DIMENSION,
        embedding_model="test-embed",
    )


def test_build_creates_index_and_maps_metadata(tmp_path: Path):
    store = _store(tmp_path)
    chunks = [make_chunk("alpha text", document_id="a", heading="A")]
    store.build(chunks, _vectors(1))
    assert store.is_loaded
    assert store.size == 1
    record = store.get_record_by_vector_id(0)
    assert record is not None
    assert record.source_path.endswith("a.md")
    assert record.heading == "A"


def test_search_returns_source_path_and_heading(tmp_path: Path):
    store = _store(tmp_path)
    store.build(
        [
            make_chunk("EGFR resistance mechanism", document_id="a", heading="耐药"),
            make_chunk("unrelated content", document_id="b", heading="其他"),
        ],
        _vectors(2),
    )
    results = store.search(_vectors(1)[0], top_k=1)
    assert len(results) == 1
    result = results[0]
    assert result.source_path.endswith("a.md")
    assert result.heading == "耐药"
    assert result.score >= 0


def test_search_k_zero_returns_empty(tmp_path: Path):
    store = _store(tmp_path)
    store.build([make_chunk("only"), make_chunk("two")], _vectors(2))
    assert store.search(_vectors(1)[0], top_k=0) == []


def test_search_k_exceeds_total_returns_all(tmp_path: Path):
    store = _store(tmp_path)
    store.build([make_chunk("one"), make_chunk("two")], _vectors(2))
    results = store.search(_vectors(1)[0], top_k=99)
    assert len(results) == 2


def test_save_load_round_trip_preserves_records(tmp_path: Path):
    store = _store(tmp_path)
    chunks = [make_chunk("needle text", document_id="a", heading="H1")]
    store.build(chunks, _vectors(1))
    saved_dir = store.save()
    assert (saved_dir / VECTORS_FILE).is_file()
    assert (saved_dir / VECTOR_IDS_FILE).is_file()
    assert (saved_dir / METADATA_FILE).is_file()

    loaded = FaissIndexStore(
        saved_dir, dimension=DIMENSION, embedding_model="test-embed"
    )
    loaded.load()
    assert loaded.size == 1
    results = loaded.search(_vectors(1)[0], top_k=1)
    assert results[0].source_path.endswith("a.md")
    assert results[0].heading == "H1"


def test_metadata_is_stored_in_independent_json(tmp_path: Path):
    store = _store(tmp_path)
    store.build([make_chunk("secret", document_id="a", heading="A")], _vectors(1))
    saved_dir = store.save()
    payload = json.loads((saved_dir / METADATA_FILE).read_text(encoding="utf-8"))
    assert payload[0]["text"] == "secret"
    assert payload[0]["source_path"].endswith("a.md")


def test_dimension_mismatch_on_load_prompts_rebuild(tmp_path: Path):
    store = _store(tmp_path)
    store.build([make_chunk("text")], _vectors(1, dimension=DIMENSION))
    saved_dir = store.save()

    different = FaissIndexStore(saved_dir, dimension=8, embedding_model="other-embed")
    with pytest.raises(EmbeddingDimensionMismatchError, match="rebuild"):
        different.load()


def test_corrupt_vectors_file_prompts_rebuild(tmp_path: Path):
    store = _store(tmp_path)
    store.build([make_chunk("text")], _vectors(1))
    saved_dir = store.save()
    (saved_dir / VECTORS_FILE).write_text("not numpy", encoding="utf-8")

    corrupt = FaissIndexStore(
        saved_dir, dimension=DIMENSION, embedding_model="test-embed"
    )
    with pytest.raises(IndexCorruptError, match="rebuild"):
        corrupt.load()


def test_missing_manifest_prompts_rebuild(tmp_path: Path):
    store = _store(tmp_path)
    store.build([make_chunk("text")], _vectors(1))
    saved_dir = store.save()
    (saved_dir / "manifest.json").unlink()

    missing = FaissIndexStore(
        saved_dir, dimension=DIMENSION, embedding_model="test-embed"
    )
    with pytest.raises(IndexCorruptError, match="rebuild"):
        missing.load()


def test_search_without_load_is_explicit(tmp_path: Path):
    store = _store(tmp_path)
    with pytest.raises(IndexNotLoadedError, match="not loaded"):
        store.search([1.0, 2.0, 3.0, 4.0], top_k=1)


def test_add_chunk_vector_mismatch_is_rejected(tmp_path: Path):
    store = _store(tmp_path)
    store.build([make_chunk("one")], _vectors(1))
    with pytest.raises(EmbeddingDimensionMismatchError, match="rebuild"):
        store.add([make_chunk("two")], _vectors(1, dimension=2))


def test_add_empty_batch_is_rejected(tmp_path: Path):
    store = _store(tmp_path)
    store.build([make_chunk("one")], _vectors(1))
    with pytest.raises(NotesRAGError, match="empty"):
        store.add([], [])


def test_read_index_metadata_reports_model_and_dimension(tmp_path: Path):
    store = _store(tmp_path)
    store.build([make_chunk("text")], _vectors(1))
    saved_dir = store.save()
    model, dimension = read_index_metadata(saved_dir)
    assert model == "test-embed"
    assert dimension == DIMENSION
