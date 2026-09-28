"""BM25 索引的精确词、中文分词与边界测试。"""

import pytest

from app.rag.bm25_store import BM25Store, tokenize_medical_text
from app.rag.schemas import Chunk
from tests.rag.conftest import make_chunk


@pytest.fixture
def medical_chunks() -> list[Chunk]:
    return [
        make_chunk("EGFR 突变患者使用奥希替尼。", document_id="egfr"),
        make_chunk("NCT04209660 研究纳入肺癌患者。", document_id="trial"),
        make_chunk("耐药机制与旁路信号通路有关。", document_id="resistance"),
    ]


@pytest.mark.parametrize(
    ("query", "expected_chunk_id"),
    [
        ("EGFR", "egfr:0"),
        ("奥希替尼", "egfr:0"),
        ("NCT04209660", "trial:0"),
    ],
)
def test_search_returns_exact_medical_term_match(
    medical_chunks, query: str, expected_chunk_id: str
) -> None:
    store = BM25Store()
    store.build(medical_chunks)

    results = store.search(query, top_k=1)

    assert results[0].chunk_id == expected_chunk_id
    assert results[0].retriever_name == "bm25"
    assert results[0].rank == 1


def test_tokenize_medical_text_preserves_alphanumeric_term_and_chinese_bigrams() -> (
    None
):
    tokens = tokenize_medical_text("EGFR 奥希替尼 NCT04209660")

    assert "egfr" in tokens
    assert "nct04209660" in tokens
    assert "奥希" in tokens


@pytest.mark.parametrize("top_k", [0, -1])
def test_search_returns_empty_for_non_positive_top_k(
    medical_chunks, top_k: int
) -> None:
    store = BM25Store()
    store.build(medical_chunks)

    assert store.search("EGFR", top_k=top_k) == []


def test_search_limits_results_when_top_k_exceeds_total(medical_chunks) -> None:
    store = BM25Store()
    store.build(medical_chunks)

    results = store.search("患者", top_k=99)
    assert len(results) <= len(medical_chunks)
    assert all(result.raw_score and result.raw_score > 0 for result in results)


def test_add_recalculates_index_for_new_exact_term(medical_chunks: list[Chunk]) -> None:
    store = BM25Store()
    store.build(medical_chunks[:1])
    store.add([medical_chunks[1]])

    results = store.search("NCT04209660", top_k=1)

    assert results[0].chunk_id == "trial:0"


def test_wp1_07_zero_bm25_score_is_not_returned_as_a_match(medical_chunks) -> None:
    store = BM25Store()
    store.build(medical_chunks)

    assert store.search("unrelated-term", top_k=5) == []
