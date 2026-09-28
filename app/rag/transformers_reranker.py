"""项目目录内已下载的 Transformers CrossEncoder；绝不在 import/request 下载。"""

import asyncio
import hashlib
from importlib import import_module
from pathlib import Path

CrossEncoderAssetSignature = tuple[tuple[str, int, int], ...]
_REQUIRED_ASSETS = ("config.json", "tokenizer.json", "model.safetensors")


class LocalModelUnavailableError(RuntimeError):
    """本地模型资产不完整或无法加载。"""


def validate_cross_encoder_assets(model_directory: Path) -> None:
    """Reject encoder-only assets that would create a random scoring head."""

    if any(not (model_directory / name).is_file() for name in _REQUIRED_ASSETS):
        raise LocalModelUnavailableError("local CrossEncoder model files are incomplete")
    try:
        safetensors = import_module("safetensors")
        with safetensors.safe_open(
            model_directory / "model.safetensors", framework="pt", device="cpu"
        ) as model:
            keys = set(model.keys())
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        raise LocalModelUnavailableError(
            "local CrossEncoder weights could not be inspected"
        ) from error
    has_classification_head = any(
        key.startswith(("classifier.", "score.")) and key.endswith("weight")
        for key in keys
    )
    if not has_classification_head:
        raise LocalModelUnavailableError(
            "local CrossEncoder classification head is missing"
        )


class TransformersCrossEncoderScorer:
    """CPU CrossEncoder scorer，模型仅从已验证的本地目录加载。"""

    config_version = "bge-reranker-base-cpu-v1"

    def __init__(self, model_directory: Path, *, revision: str) -> None:
        self._model_directory = model_directory
        self._revision = revision
        self.model_version = f"BAAI/bge-reranker-base@{revision}"
        self._model = None

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        model = self._load_model()
        try:
            values = model.predict([(query, text) for text in texts], show_progress_bar=False)
        except (RuntimeError, ValueError) as error:
            raise LocalModelUnavailableError("local CrossEncoder inference failed") from error
        return [float(value) for value in values]

    async def score_async(self, query: str, texts: list[str]) -> list[float]:
        return await asyncio.to_thread(self.score, query, texts)

    def load(self) -> None:
        """Eagerly load the already-validated local model on the caller's thread."""

        self._load_model()

    def _load_model(self):
        if any(not (self._model_directory / name).is_file() for name in _REQUIRED_ASSETS):
            raise LocalModelUnavailableError("local CrossEncoder model files are incomplete")
        if self._model is not None:
            return self._model
        try:
            CrossEncoder = import_module("sentence_transformers").CrossEncoder
            self._model = CrossEncoder(str(self._model_directory), device="cpu")
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            raise LocalModelUnavailableError("local CrossEncoder model could not be loaded") from error
        return self._model


def create_bge_reranker(
    model_directory: Path,
    *,
    revision: str | None = None,
) -> TransformersCrossEncoderScorer:
    """Create an offline scorer whose version identifies the actual local assets."""

    return TransformersCrossEncoderScorer(
        model_directory,
        revision=revision or fingerprint_cross_encoder_assets(model_directory),
    )


def cross_encoder_asset_signature(
    model_directory: Path,
) -> CrossEncoderAssetSignature:
    """Return a lightweight identity used to detect changes during model loading."""

    paths = [model_directory / name for name in _REQUIRED_ASSETS]
    if any(not path.is_file() for path in paths):
        return ()
    return tuple(
        (path.name, path.stat().st_size, path.stat().st_mtime_ns) for path in paths
    )


def fingerprint_cross_encoder_assets(model_directory: Path) -> str:
    """Hash the exact required asset bytes used to identify one local model."""

    paths = [model_directory / name for name in _REQUIRED_ASSETS]
    if any(not path.is_file() for path in paths):
        return "unavailable"
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        with path.open("rb") as asset:
            while block := asset.read(8 * 1024 * 1024):
                digest.update(block)
    return f"sha256:{digest.hexdigest()[:16]}"
