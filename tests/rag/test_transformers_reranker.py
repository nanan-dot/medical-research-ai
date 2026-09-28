import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.rag.reranker import RerankCandidate, RerankerService
from app.rag.transformers_reranker import (
    LocalModelUnavailableError,
    create_bge_reranker,
)


def test_cross_encoder_factory_marks_missing_assets_and_fails_lazily(tmp_path) -> None:
    scorer = create_bge_reranker(tmp_path)

    assert scorer.model_version.endswith("unavailable")
    with pytest.raises(LocalModelUnavailableError, match="incomplete"):
        scorer.score("sotorasib", ["KRAS G12C"])


def test_cross_encoder_model_version_changes_with_asset_content(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for directory, weight_content in ((first, "weights-a"), (second, "weights-b")):
        directory.mkdir()
        (directory / "config.json").write_text("config", encoding="utf-8")
        (directory / "tokenizer.json").write_text("tokenizer", encoding="utf-8")
        (directory / "model.safetensors").write_text(weight_content, encoding="utf-8")

    first_scorer = create_bge_reranker(first)
    second_scorer = create_bge_reranker(second)

    assert first_scorer.model_version.startswith("BAAI/bge-reranker-base@sha256:")
    assert first_scorer.model_version != second_scorer.model_version


def test_cross_encoder_loads_only_complete_local_assets_on_cpu(tmp_path, monkeypatch) -> None:
    for filename in ("config.json", "tokenizer.json", "model.safetensors"):
        (tmp_path / filename).write_text("local", encoding="utf-8")

    received: dict[str, object] = {}

    class FakeCrossEncoder:
        def __init__(self, directory: str, *, device: str) -> None:
            received.update(directory=directory, device=device)

        def predict(self, pairs: list[tuple[str, str]], **_kwargs: object) -> list[float]:
            return [float(index) for index, _pair in enumerate(pairs, start=1)]

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(CrossEncoder=FakeCrossEncoder))
    scorer = create_bge_reranker(tmp_path)

    assert scorer.score("sotorasib", ["KRAS G12C", "adagrasib"]) == [1.0, 2.0]
    assert received == {"directory": str(tmp_path), "device": "cpu"}


def test_unavailable_bge_safely_falls_back_to_baseline_order() -> None:
    scorer = create_bge_reranker(Path("missing-local-bge"))
    results = RerankerService(scorer).rerank(
        "KRAS G12C", [RerankCandidate("a", "first", 1), RerankCandidate("b", "second", 2)]
    )
    assert [item.candidate.document_id for item in results] == ["a", "b"]
    assert all(item.fallback for item in results)
