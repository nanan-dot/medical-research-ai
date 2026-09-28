import asyncio
from pathlib import Path

from app.modules.medical_translation.provider import (
    LocalMarianTranslationProvider,
    _protect_affiliation_names,
    _restore_glossary_terms,
    _restore_protected_names,
)


class _Encoded(dict):
    pass


class _Tokenizer:
    def __call__(self, value, **_kwargs):
        text = value[0] if isinstance(value, list) else value
        return _Encoded(input_ids=list(range(len(text) + 2)), attention_mask=[1])

    def batch_decode(self, generated, **_kwargs):
        return [generated[0]]


class _Tensor:
    def to(self, _device):
        return self


class _BatchTokenizer(_Tokenizer):
    def __call__(self, value, **kwargs):
        if isinstance(value, list):
            assert kwargs.get("truncation") is False
            return _Encoded(input_ids=_Tensor(), attention_mask=_Tensor())
        return super().__call__(value, **kwargs)


class _Torch:
    class inference_mode:
        def __enter__(self):
            return None

        def __exit__(self, *_args):
            return None


class _Model:
    def generate(self, **_kwargs):
        return ["译文"]


def test_local_provider_chunks_without_silent_truncation_and_reports_real_spans(monkeypatch) -> None:
    provider = LocalMarianTranslationProvider(Path("."))
    tokenizer = _BatchTokenizer()
    monkeypatch.setattr(
        provider,
        "_load",
        lambda: (tokenizer, _Model(), _Torch(), "cpu", None, "local-test"),
    )
    source = "A" * 1200

    result = asyncio.run(
        provider.translate(
            source_text=source,
            source_language="en",
            target_language="zh-CN",
        )
    )

    assert len(result.alignment) >= 3
    assert result.alignment[0].source_start == 0
    assert result.alignment[-1].source_end == len(source)
    assert all(
        left.source_end == right.source_start
        for left, right in zip(result.alignment, result.alignment[1:])
    )


def test_glossary_restoration_is_case_insensitive_but_never_replaces_substrings() -> None:
    translated = _restore_glossary_terms(
        "ILD is distinct from childhood.",
        "ILD and childhood remain ILD-like",
        {"ild": "间质性肺病", "child": "儿童"},
    )
    assert translated == "间质性肺病 and childhood remain 间质性肺病-like"


def test_affiliation_names_are_masked_and_restored_without_model_invention() -> None:
    source = (
        "Department of Respiratory Medicine, Medical School, University of Crete, "
        "Heraklion, Greece."
    )

    masked, protected = _protect_affiliation_names(source)

    assert "University of Crete" not in masked
    assert "Heraklion" not in masked
    assert "Greece" not in masked
    assert _restore_protected_names(masked, protected) == source
