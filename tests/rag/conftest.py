"""Mini-RAG 测试共用替身与 fixture。

``FakeEmbeddingClient`` 是轻量测试替身：返回与文本哈希相关的确定性向量，
用于验证管道正确传递文本、维度一致，不依赖 numpy/faiss/dummy 的真实实现。
"""

from pathlib import Path

import pytest

from app.rag.schemas import Chunk


class FakeEmbeddingClient:
    """确定性测试替身：同一文本总是得到同一向量（哈希派生）。"""

    model_name = "fake-test"

    def __init__(self, dimension: int = 8) -> None:
        self.dimension_value = dimension

    @property
    def dimension(self) -> int:
        return self.dimension_value

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(byte) / 255.0 for byte in text.encode("utf-8")[: self.dimension_value]] for text in texts]


@pytest.fixture
def fake_embedding() -> FakeEmbeddingClient:
    return FakeEmbeddingClient()


def make_chunk(text: str, document_id: str = "doc", heading: str = "h") -> Chunk:
    chunk = Chunk(
        chunk_id=f"{document_id}:0",
        document_id=document_id,
        heading=heading,
        text=text,
        source_path=f"/notes/{document_id}.md",
    )
    chunk.validate_text()
    return chunk


def write_sample_note(tmp_path: Path, name: str = "note.md", body: str = "") -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path
