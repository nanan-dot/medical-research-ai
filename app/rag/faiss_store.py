"""FAISS 向量索引存储：索引构建/保存/加载/检索 + 元数据独立 JSON。

设计边界（必须显式说明）：
- **FAISS 不保存元数据**：向量文件只存 ``(向量, vector_id)``，chunk_id/heading/text/
  source_path 全部落在独立的 ``metadata.json``；检索按 vector_id 回查。
- **维度校验**：加载时比对已存索引维度与当前 Embedding 维度，不匹配抛
  ``EmbeddingDimensionMismatchError``（提示重建，不静默截断）。
- **损坏处理**：反序列化失败抛 ``IndexCorruptError`` 并给出重建指引，不静默吞掉。
"""

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import ValidationError

from app.rag.exceptions import (
    EmbeddingDimensionMismatchError,
    IndexCorruptError,
    IndexNotLoadedError,
    NotesRAGError,
)
from app.rag.schemas import Chunk, IndexMetadata, RetrievalResult, VectorChunkRecord

logger = logging.getLogger(__name__)

INDEX_FORMAT_VERSION = 1

# numpy 保存的向量数组文件名（相对索引目录）
VECTORS_FILE = "vectors.npy"
# vector_id 数组文件名（相对索引目录）
VECTOR_IDS_FILE = "vector_ids.npy"
# 元数据 JSON 文件名（相对索引目录）
METADATA_FILE = "metadata.json"
# 索引描述信息文件名（相对索引目录）
MANIFEST_FILE = "manifest.json"

_MIN_CHUNK_LIMIT = 1


def _manifest_payload(embedding_model: str, dimension: int) -> dict[str, object]:
    return {
        "format_version": INDEX_FORMAT_VERSION,
        "embedding_model": embedding_model,
        "dimension": dimension,
    }


def _load_manifest(index_dir: Path) -> tuple[str, int]:
    manifest_path = index_dir / MANIFEST_FILE
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise IndexCorruptError(
            f"index manifest is missing or unreadable at {manifest_path}; rebuild the index"
        ) from error
    if not isinstance(payload, dict):
        raise IndexCorruptError("index manifest must be a JSON object; rebuild the index")
    format_version = payload.get("format_version")
    dimension = payload.get("dimension")
    embedding_model = payload.get("embedding_model")
    if format_version != INDEX_FORMAT_VERSION:
        raise IndexCorruptError(
            f"unsupported index format {format_version!r}; rebuild the index"
        )
    if not isinstance(dimension, int) or dimension <= 0:
        raise IndexCorruptError("index manifest has an invalid dimension; rebuild the index")
    if not isinstance(embedding_model, str) or not embedding_model:
        raise IndexCorruptError("index manifest is missing the embedding model; rebuild the index")
    return embedding_model, dimension


def read_index_metadata(index_dir: Path) -> tuple[str, int]:
    """读取索引目录的描述信息（embedding_model, dimension）。

    供加载方在构造 store 前预先拿到维度做加载前校验。
    """
    return _load_manifest(Path(index_dir))


def _write_json_atomic(path: Path, payload: Any) -> None:
    """先写临时文件再原子替换，避免进程中断留下半截 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class FaissIndexStore:
    """FAISS L2 索引 + 独立 JSON 元数据的存储与检索。

    线程模型：同步方法，索引操作由调用方（如 CLI）串行执行；
    不要在多个协程中并发调用本类方法。
    """

    def __init__(
        self,
        index_dir: Path,
        *,
        dimension: int,
        embedding_model: str,
    ) -> None:
        self.index_dir = Path(index_dir)
        self.dimension = dimension
        self.embedding_model = embedding_model
        self._index: Any = None
        self._metadata: dict[int, VectorChunkRecord] = {}
        self._chunk_id_to_vector_id: dict[str, int] = {}

    @property
    def is_loaded(self) -> bool:
        return self._index is not None

    @property
    def size(self) -> int:
        return int(self._index.ntotal) if self._index is not None else 0

    def build(self, chunks: list[Chunk], vectors: list[list[float]]) -> IndexMetadata:
        """从分块与向量重建空索引并写入第一批数据。

        :raises NotesRAGError: 分块与向量数量不一致，或向量维度不匹配
        """
        self._ensure_matching_vectors(chunks, vectors)
        vector_count = len(vectors)
        self._index = self._create_index(self.dimension)
        if vector_count:
            self.add(chunks, vectors)
        return IndexMetadata(
            embedding_model=self.embedding_model,
            dimension=self.dimension,
            document_count=len({chunk.document_id for chunk in chunks}),
            chunk_count=len(chunks),
        )

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> IndexMetadata:
        """向已建立的索引追加分块与向量，并写回元数据映射。"""
        self._require_loaded()
        if not chunks:
            raise NotesRAGError("cannot add an empty chunk batch")
        self._ensure_matching_vectors(chunks, vectors)
        self._validate_vectors(vectors)

        vector_ids: list[int] = []
        for chunk, vector in zip(chunks, vectors):
            vector_id = self.size
            self._index.add(np.asarray([vector], dtype="float32"))
            vector_ids.append(vector_id)
            record = VectorChunkRecord(
                vector_id=vector_id,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                heading=chunk.heading,
                text=chunk.text,
                source_path=chunk.source_path,
            )
            self._metadata[vector_id] = record
            self._chunk_id_to_vector_id[chunk.chunk_id] = vector_id

        return IndexMetadata(
            embedding_model=self.embedding_model,
            dimension=self.dimension,
            document_count=len({chunk.document_id for chunk in chunks}),
            chunk_count=len(chunks),
        )

    def search(self, query_vector: list[float], top_k: int = 5) -> list[RetrievalResult]:
        """L2 最近邻检索并回查元数据。

        :param query_vector: 查询文本的向量
        :param top_k: 返回条数（0 返回空，超总量返回全部）
        """
        self._require_loaded()
        self._validate_query_vector(query_vector)
        if top_k < _MIN_CHUNK_LIMIT or self.size == 0:
            return []
        k = min(top_k, self.size)
        distances, indices = self._index.search(
            np.asarray([query_vector], dtype="float32"), k
        )
        results: list[RetrievalResult] = []
        for distance, vector_id in zip(distances[0], indices[0]):
            if vector_id < 0:
                continue
            record = self._metadata.get(int(vector_id))
            if record is None:
                raise IndexCorruptError(
                    f"vector_id {vector_id} has no metadata record; rebuild the index"
                )
            results.append(
                RetrievalResult(
                    text=record.text,
                    source_path=record.source_path,
                    heading=record.heading,
                    score=float(distance),
                )
            )
        return results

    def save(self, index_dir: Path | None = None) -> Path:
        """把索引与元数据持久化到目录。

        :return: 实际写入的索引目录
        """
        self._require_loaded()
        target_dir = self.index_dir if index_dir is None else Path(index_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(target_dir / MANIFEST_FILE, _manifest_payload(self.embedding_model, self.dimension))
        np.save(target_dir / VECTORS_FILE, self._extract_vectors())
        np.save(target_dir / VECTOR_IDS_FILE, np.asarray(list(self._metadata.keys()), dtype="int64"))
        self._save_metadata_records(target_dir)
        logger.info("saved faiss index to %s with %d vectors", target_dir, self.size)
        return target_dir

    def load(self, index_dir: Path | None = None) -> None:
        """从目录加载索引；维度或格式不匹配时显式抛错提示重建。"""
        target_dir = self.index_dir if index_dir is None else Path(index_dir)
        embedding_model, stored_dimension = _load_manifest(target_dir)
        if stored_dimension != self.dimension:
            raise EmbeddingDimensionMismatchError(
                f"stored index dimension {stored_dimension} != current embedding dimension "
                f"{self.dimension}; rebuild the index with the current embedding model"
            )
        vectors_path = target_dir / VECTORS_FILE
        vector_ids_path = target_dir / VECTOR_IDS_FILE
        if not vectors_path.is_file() or not vector_ids_path.is_file():
            raise IndexCorruptError(
                f"index files are missing in {target_dir}; rebuild the index"
            )
        try:
            vectors = np.load(vectors_path, allow_pickle=False)
            vector_ids = np.load(vector_ids_path, allow_pickle=False)
        except (ValueError, OSError) as error:
            raise IndexCorruptError(
                f"index vectors are unreadable in {target_dir}; rebuild the index"
            ) from error

        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise IndexCorruptError(
                f"index vector shape {vectors.shape} does not match dimension "
                f"{self.dimension}; rebuild the index"
            )
        if vector_ids.ndim != 1 or len(vector_ids) != len(vectors):
            raise IndexCorruptError(
                "index vector ids are inconsistent with vectors; rebuild the index"
            )

        metadata = self._load_metadata_records(target_dir)
        expected_ids = {int(vector_id) for vector_id in vector_ids.tolist()}
        if set(metadata.keys()) != expected_ids:
            raise IndexCorruptError(
                "metadata vector ids do not match the stored vectors; rebuild the index"
            )

        index = self._create_index(self.dimension)
        index.add(vectors)
        self._index = index
        self._metadata = metadata
        self._chunk_id_to_vector_id = {
            record.chunk_id: record.vector_id for record in metadata.values()
        }
        logger.info("loaded faiss index from %s with %d vectors", target_dir, self.size)

    def reset(self) -> None:
        """清空内存中的索引与映射（便于重建流程复用同一 store）。"""
        self._index = None
        self._metadata = {}
        self._chunk_id_to_vector_id = {}

    def get_record_by_vector_id(self, vector_id: int) -> VectorChunkRecord | None:
        return self._metadata.get(vector_id)

    def _create_index(self, dimension: int) -> Any:
        try:
            import faiss
        except ImportError as error:
            raise NotesRAGError(
                "faiss-cpu is required; install the 'rag' optional dependency group"
            ) from error
        return faiss.IndexFlatL2(dimension)

    def _require_loaded(self) -> None:
        if self._index is None:
            raise IndexNotLoadedError(
                "index is not loaded; call build() or load() before adding/searching"
            )

    def _ensure_matching_vectors(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise NotesRAGError(
                f"chunk count {len(chunks)} does not match vector count {len(vectors)}"
            )

    def _validate_vectors(self, vectors: list[list[float]]) -> None:
        for vector in vectors:
            if len(vector) != self.dimension:
                raise EmbeddingDimensionMismatchError(
                    f"embedding produced dimension {len(vector)} but the index expects "
                    f"{self.dimension}; rebuild the index with the current embedding model"
                )

    def _validate_query_vector(self, query_vector: list[float]) -> None:
        if not query_vector or len(query_vector) != self.dimension:
            raise EmbeddingDimensionMismatchError(
                f"query vector dimension {len(query_vector)} does not match the index "
                f"dimension {self.dimension}; embed the query with the same model"
            )

    def _extract_vectors(self) -> np.ndarray:
        """从 FAISS 索引导出全部向量。"""
        vectors = self._index.reconstruct_n(0, self.size)
        return np.asarray(vectors, dtype="float32").reshape(self.size, self.dimension)

    def _save_metadata_records(self, target_dir: Path) -> None:
        payload = [record.model_dump() for record in self._metadata.values()]
        _write_json_atomic(target_dir / METADATA_FILE, payload)

    def _load_metadata_records(self, target_dir: Path) -> dict[int, VectorChunkRecord]:
        metadata_path = target_dir / METADATA_FILE
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as error:
            raise IndexCorruptError(
                f"metadata file is missing or unreadable at {metadata_path}; rebuild the index"
            ) from error
        if not isinstance(payload, list):
            raise IndexCorruptError("metadata file must contain a JSON list; rebuild the index")
        records: dict[int, VectorChunkRecord] = {}
        for item in payload:
            if not isinstance(item, dict):
                raise IndexCorruptError("metadata file contains a non-object record; rebuild the index")
            try:
                record = VectorChunkRecord.model_validate(item)
            except ValidationError as error:
                raise IndexCorruptError(
                    "metadata file contains an invalid record; rebuild the index"
                ) from error
            records[record.vector_id] = record
        return records
