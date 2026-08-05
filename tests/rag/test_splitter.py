"""Splitter 切片测试（标题切片 + 固定长度回退）。"""

from pathlib import Path


from app.rag.schemas import SplitStrategy
from app.rag.splitter import split_markdown_document


def test_heading_split_preserves_heading_and_skips_empty(tmp_path: Path):
    content = "# Overview\nIntro paragraph\n## Methods\nDetails\n"
    chunks = split_markdown_document(
        content, document_id="note", source_path=str(tmp_path / "note.md")
    )
    assert [(chunk.heading, chunk.text) for chunk in chunks] == [
        ("Overview", "Intro paragraph"),
        ("Methods", "Details"),
    ]
    assert chunks[0].source_path == str(tmp_path / "note.md")


def test_untitled_body_becomes_untitled_chunk():
    chunks = split_markdown_document("lead-in text", document_id="doc")
    assert len(chunks) == 1
    assert chunks[0].heading == ""
    assert chunks[0].text == "lead-in text"


def test_empty_markdown_produces_no_chunks():
    assert split_markdown_document("", document_id="doc") == []
    assert split_markdown_document("# Title only", document_id="doc") == []


def test_whitespace_only_block_is_skipped():
    chunks = split_markdown_document("# Title\n   \n", document_id="doc")
    assert chunks == []


def test_fixed_length_mode_with_overlap():
    strategy = SplitStrategy(mode="fixed_length", chunk_size=8, overlap=2)
    chunks = split_markdown_document("abcdefghijklmnop", document_id="doc", strategy=strategy)
    # 滑动窗口语义：step = chunk_size - overlap = 6，因此第二块从下标 6 开始。
    assert chunks[0].text == "abcdefgh"
    assert "ghijklmn" in [chunk.text for chunk in chunks]
    assert all(chunk.heading == "" for chunk in chunks)


def test_long_heading_section_falls_back_to_fixed_length():
    content = "# Long\n" + "x" * 50 + "\n# Next\nnext section\n"
    strategy = SplitStrategy(chunk_size=20, overlap=4)
    chunks = split_markdown_document(content, document_id="doc", strategy=strategy)
    long_chunks = [chunk for chunk in chunks if chunk.heading == "Long"]
    next_chunks = [chunk for chunk in chunks if chunk.heading == "Next"]
    assert len(long_chunks) >= 2
    assert len(next_chunks) == 1
    assert next_chunks[0].text == "next section"


def test_chunk_ids_are_globally_unique_across_heading_blocks():
    content = "# A\n" + "y" * 30 + "\n# B\nz" * 30
    strategy = SplitStrategy(chunk_size=10)
    chunks = split_markdown_document(content, document_id="doc", strategy=strategy)
    ids = [chunk.chunk_id for chunk in chunks]
    assert len(ids) == len(set(ids))


def test_fixed_length_with_overlap_greater_than_chunk_size_is_capped():
    strategy = SplitStrategy(mode="fixed_length", chunk_size=5, overlap=99)
    chunks = split_markdown_document("0123456789", document_id="doc", strategy=strategy)
    # overlap 收敛到 chunk_size-1=4，步长为 1，全程滑动 → 10 块
    assert len(chunks) == 10
    assert chunks[0].text == "01234"
    assert chunks[-1].text == "9"
