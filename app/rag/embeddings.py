"""Embedding 客户端抽象与实现（本地优先 + 开发兜底）。

设计意图：
- 本地优先：Ollama 是本机零成本方案，数据不出机器；
- 云端禁止：ollama 失败时用 dummy 兜底而非切换云端（对齐 R2-WP09 通用禁止）；
- dummy 只用于开发与离线测试，返回确定性哈希向量，**非语义向量**，文档明确标注。
"""

import hashlib
import ipaddress
from typing import Literal, Protocol, runtime_checkable
from urllib.parse import urlparse

import httpx

from app.rag.exceptions import NotesRAGError

DUMMY_EMBEDDING_DIMENSION = 16


class EmbeddingError(NotesRAGError):
    """Embedding 生成失败。"""

    code = "embedding_error"


class EmbeddingDimensionError(EmbeddingError):
    """生成的向量维度与声明的模型维度不一致。"""

    code = "embedding_dimension_error"


@runtime_checkable
class EmbeddingClient(Protocol):
    """Embedding 客户端的最小接口（可注入实现，便于测试替身）。"""

    @property
    def dimension(self) -> int:
        """当前模型输出的向量维度。"""
        ...

    @property
    def model_name(self) -> str:
        """模型标识，用于索引元数据与重建提示。"""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """把一批文本转成向量。"""
        ...


class DummyEmbeddingClient:
    """开发用确定性哈希向量客户端（非语义向量）。

    用途：离线测试、管道冒烟验证、无 Ollama 时的兜底。向量仅由文本哈希
    派生，不携带语义；任何依赖它做语义检索的用法都是无效的。
    """

    model_name = "dummy-hash"

    def __init__(self, dimension: int = DUMMY_EMBEDDING_DIMENSION) -> None:
        if dimension <= 0:
            raise EmbeddingError(f"dummy embedding dimension must be positive, got {dimension}")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # 均匀铺满 dimension：重复哈希直到长度足够，再归一化到单位长度
        seed = digest
        values: list[int] = []
        while len(values) < self._dimension:
            values.extend(seed)
            seed = hashlib.sha256(seed).digest()
        selected = values[: self._dimension]
        scale = 1.0 / max(max(abs(value) for value in selected), 1)
        return [value * scale for value in selected]


class OllamaEmbeddingClient:
    """基于本机 Ollama ``/api/embed`` 的本地 Embedding 客户端。

    设计说明：直接调用 Ollama 原生接口，不经过 LLMClient（LLMClient 只支持
    chat），也不使用 OpenAI 兼容端点；服务不可达时抛 ``EmbeddingError``，
    由调用方决定是否回退到 dummy——**绝不自动切换云端**。
    """

    model_name: str

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
        http_client: httpx.AsyncClient | None = None,
        declared_dimension: int | None = None,
    ) -> None:
        if not base_url.rstrip("/"):
            raise EmbeddingError("OLLAMA_BASE_URL must not be empty")
        if not model.strip():
            raise EmbeddingError("OLLAMA_EMBEDDING_MODEL must not be empty")
        if declared_dimension is not None and declared_dimension <= 0:
            raise EmbeddingError(
                f"declared embedding dimension must be positive, got {declared_dimension}"
            )
        _validate_local_base_url(base_url)
        self.base_url = base_url.rstrip("/")
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            timeout=timeout_seconds, trust_env=False
        )
        self._declared_dimension = declared_dimension
        self._dimension: int | None = None

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            raise EmbeddingError(
                "ollama embedding dimension is unknown until the first embed call"
            )
        return self._dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self._http_client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model_name, "input": texts},
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as error:
            raise EmbeddingError("ollama embedding request timed out") from error
        except httpx.TransportError as error:
            raise EmbeddingError(
                "ollama embedding service is unreachable; start the local Ollama service"
            ) from error

        if response.status_code >= 400:
            raise EmbeddingError(
                f"ollama embedding service returned HTTP {response.status_code}"
            )
        try:
            payload = response.json()
            embeddings = payload.get("embeddings")
        except ValueError as error:
            raise EmbeddingError("ollama returned a non-JSON embedding response") from error

        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise EmbeddingError("ollama embedding response is incompatible with the input")

        vector_dimension: int | None = None
        normalized: list[list[float]] = []
        for embedding in embeddings:
            if not isinstance(embedding, list):
                raise EmbeddingError("ollama returned a non-list embedding")
            if not all(isinstance(value, (int, float)) for value in embedding):
                raise EmbeddingError("ollama embedding contains non-numeric values")
            flat = [float(value) for value in embedding]
            if vector_dimension is None:
                vector_dimension = len(flat)
            elif len(flat) != vector_dimension:
                raise EmbeddingError("ollama returned embeddings of inconsistent dimensions")
            normalized.append(flat)

        if vector_dimension is None or vector_dimension == 0:
            raise EmbeddingError("ollama returned empty embeddings")

        if self._declared_dimension is not None and vector_dimension != self._declared_dimension:
            raise EmbeddingDimensionError(
                f"ollama embedding dimension {vector_dimension} does not match the configured "
                f"EMBEDDING_DIMENSION {self._declared_dimension}; set EMBEDDING_DIMENSION "
                "to the actual model output dimension or leave it empty"
            )
        if self._dimension is not None and self._dimension != vector_dimension:
            raise EmbeddingDimensionError(
                f"ollama embedding dimension changed from {self._dimension} to {vector_dimension}"
            )
        self._dimension = vector_dimension
        return normalized

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def __aenter__(self) -> "OllamaEmbeddingClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


ProviderName = Literal["ollama", "dummy"]


def create_embedding_client(
    *,
    provider: str,
    base_url: str,
    model: str,
    timeout_seconds: float = 120.0,
    dimension: int | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> EmbeddingClient:
    """按配置创建 Embedding 客户端（工厂）。

    :param provider: ``ollama``（本地优先）或 ``dummy``（开发兜底）
    :param base_url: Ollama 服务地址（provider=dummy 时忽略）
    :param model: Ollama 模型名（provider=dummy 时忽略）
    :param timeout_seconds: Ollama 请求超时
    :param dimension: dummy 客户端维度；或 Ollama 声明维度（校验响应一致）
    """
    if provider == "dummy":
        return DummyEmbeddingClient(dimension=dimension or DUMMY_EMBEDDING_DIMENSION)
    if provider == "ollama":
        return OllamaEmbeddingClient(
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            http_client=http_client,
            declared_dimension=dimension,
        )
    raise EmbeddingError(f"unsupported embedding provider: {provider}")


def _validate_local_base_url(value: str) -> None:
    """只允许回环地址，防止 embedding 请求把笔记内容发往外部服务。"""
    parsed = urlparse(value)
    if parsed.scheme != "http" or not parsed.hostname:
        raise EmbeddingError("OLLAMA_BASE_URL must be a local HTTP URL")
    try:
        is_loopback = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        is_loopback = parsed.hostname == "localhost"
    if not is_loopback:
        raise EmbeddingError("OLLAMA_BASE_URL must use localhost or a loopback address")
