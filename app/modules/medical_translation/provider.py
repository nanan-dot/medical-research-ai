"""Injectable structured translation provider with an existing-model adapter."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Protocol

from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, TemporarilyUnavailableError
from app.core.security import SecretCipher
from app.integrations.llm.client import LLMClient
from app.integrations.llm.schemas import ChatMessage, LLMConfig
from app.integrations.ollama.client import OllamaClient
from app.modules.medical_translation.terminology_dataset import (
    MedicalTerminologyDataset,
)
from app.modules.model_config.model import ModelConfig


class AlignmentSpan(BaseModel):
    source_start: int = Field(ge=0)
    source_end: int = Field(gt=0)
    target_start: int = Field(ge=0)
    target_end: int = Field(gt=0)


class TranslationProviderResult(BaseModel):
    translated_text: str = Field(min_length=1, max_length=16000)
    alignment: list[AlignmentSpan] = Field(min_length=1, max_length=512)
    provider: str
    model: str
    model_revision: str = "unknown"


class TranslationProvider(Protocol):
    async def translate(
        self,
        *,
        source_text: str,
        source_language: str,
        target_language: str,
        glossary: dict[str, str] | None = None,
    ) -> TranslationProviderResult: ...


class OllamaMedicalTranslationProvider:
    """Local constrained-JSON medical translation using an installed Ollama model."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        terminology_dataset: MedicalTerminologyDataset | None = None,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._terminology_dataset = terminology_dataset

    async def translate(
        self,
        *,
        source_text: str,
        source_language: str,
        target_language: str,
        glossary: dict[str, str] | None = None,
    ) -> TranslationProviderResult:
        if (source_language, target_language) != ("en", "zh-CN"):
            raise TemporarilyUnavailableError("Ollama medical translator supports only en to zh-CN")
        if not source_text.strip() or len(source_text) > 8_000:
            raise TemporarilyUnavailableError("Translation input exceeds local limit")
        reserved_terms = (*_CORE_MEDICAL_GLOSSARY, *(glossary or {}))
        dataset_terms = (
            self._terminology_dataset.lookup(source_text, reserved_terms=reserved_terms)
            if self._terminology_dataset is not None
            else {}
        )
        effective_glossary = {
            **dataset_terms,
            **_CORE_MEDICAL_GLOSSARY,
            **(glossary or {}),
        }
        protected_source, protected_names = _protect_affiliation_names(source_text)
        system = (
            "You are a conservative professional medical translator. Translate English into "
            "Simplified Chinese using standard Chinese medical terminology. Preserve every number, "
            "comparator, unit, dose, frequency, negation, uncertainty, group direction, abbreviation "
            "and statistical measure. Preserve personal names, institution names and geographic names "
            "in their original Latin spelling when a verified Chinese name is not supplied; never invent "
            "a transliteration or location. Apply the supplied glossary exactly. Do not add, omit, explain "
            "or summarize any claim. Return only the translated_text JSON field."
        )
        user = json.dumps(
            {
                "source_text": protected_source,
                "document_glossary": effective_glossary,
                "protected_tokens": list(protected_names),
            },
            ensure_ascii=False,
        )
        async with OllamaClient(
            base_url=self._base_url,
            model=self._model,
            timeout_seconds=self._timeout_seconds,
        ) as client:
            payload = await client.generate_json(
                [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
                {
                    "type": "object",
                    "properties": {"translated_text": {"type": "string"}},
                    "required": ["translated_text"],
                    "additionalProperties": False,
                },
            )
        translated = payload.get("translated_text")
        if not isinstance(translated, str) or not translated.strip():
            raise TemporarilyUnavailableError("Ollama returned an empty translation")
        translated = _restore_protected_names(translated, protected_names)
        result = TranslationProviderResult(
            translated_text=translated.strip(),
            alignment=[AlignmentSpan(
                source_start=0,
                source_end=len(source_text),
                target_start=0,
                target_end=len(translated.strip()),
            )],
            provider="ollama-local",
            model=self._model,
            model_revision="local-installed",
        )
        _validate_alignment(result, len(source_text))
        return result


_CORE_MEDICAL_GLOSSARY = {
    "interstitial lung disease": "间质性肺病",
    "connective tissue disease": "结缔组织病",
    "pulmonary function test": "肺功能检查",
    "pulmonary function tests": "肺功能检查",
    "high-resolution computed tomography": "高分辨率计算机断层扫描",
    "respiratory medicine": "呼吸医学",
    "pneumonology": "肺病学",
    "pulmonology": "呼吸病学",
    "rheumatology": "风湿病学",
    "morbidity": "发病率",
    "mortality": "死亡率",
    "sensitivity": "灵敏度",
    "specificity": "特异性",
    "systemic lupus erythematosus": "系统性红斑狼疮",
    "rheumatoid arthritis": "类风湿关节炎",
    "forced vital capacity": "用力肺活量",
    "adverse event": "不良事件",
    "adverse events": "不良事件",
}

_AFFILIATION_MARKER = re.compile(
    r"\b(?:department|laboratory|medical school|university|hospital|institute|"
    r"centre|center|faculty)\b",
    re.IGNORECASE,
)
_NAMED_INSTITUTION = re.compile(
    r"\b(?:University|Hospital|Institute|Centre|Center|Network|Society|Alliance|"
    r"College)\s+of\s+[A-Z][A-Za-z'\N{RIGHT SINGLE QUOTATION MARK}-]*"
    r"(?:\s+[A-Z][A-Za-z'\N{RIGHT SINGLE QUOTATION MARK}-]*){0,3}\b"
)
_SHORT_PROPER_COMPONENT = re.compile(
    r"[A-Z][A-Za-z'\N{RIGHT SINGLE QUOTATION MARK}-]*"
    r"(?:\s+[A-Z][A-Za-z'\N{RIGHT SINGLE QUOTATION MARK}-]*){0,2}"
)


def _protect_affiliation_names(source_text: str) -> tuple[str, dict[str, str]]:
    """Mask affiliation proper names so a model cannot invent another location."""
    if not _AFFILIATION_MARKER.search(source_text):
        return source_text, {}

    spans = [match.span() for match in _NAMED_INSTITUTION.finditer(source_text)]
    components = list(re.finditer(r"[^,;\n]+", source_text))
    for component in components[-2:]:
        raw = component.group(0)
        stripped = raw.strip().rstrip(".")
        if _SHORT_PROPER_COMPONENT.fullmatch(stripped):
            start = component.start() + raw.index(stripped)
            spans.append((start, start + len(stripped)))

    selected: list[tuple[int, int]] = []
    for start, end in sorted(set(spans)):
        if not any(start < kept_end and end > kept_start for kept_start, kept_end in selected):
            selected.append((start, end))
    if not selected:
        return source_text, {}

    protected: dict[str, str] = {}
    masked = source_text
    for index, (start, end) in reversed(list(enumerate(selected))):
        token = f"ZXQPN{index}QXZ"
        protected[token] = source_text[start:end]
        masked = f"{masked[:start]}{token}{masked[end:]}"
    return masked, protected


def _restore_protected_names(value: str, protected: dict[str, str]) -> str:
    restored = value
    for token, original in protected.items():
        if token not in restored:
            raise TemporarilyUnavailableError(
                f"Ollama omitted protected proper name token {token}"
            )
        restored = restored.replace(token, original)
    return restored


class ConfiguredTranslationProvider:
    """Calls only the configured default model and validates strict JSON output."""

    def __init__(self, config: ModelConfig, *, api_key: str | None = None) -> None:
        self._config = config
        self._api_key = api_key

    @classmethod
    async def from_session(cls, session: AsyncSession) -> ConfiguredTranslationProvider:
        config = await session.scalar(
            select(ModelConfig).where(ModelConfig.is_default.is_(True))
        )
        if config is None:
            raise TemporarilyUnavailableError(
                "No default translation model is configured"
            )
        if config.provider != "ollama" and not config.allow_cloud_content:
            raise ConflictError(
                "The configured cloud model is not allowed to receive document content"
            )
        key = (
            SecretCipher().decrypt(config.encrypted_api_key)
            if config.encrypted_api_key
            else None
        )
        return cls(config, api_key=key)

    async def translate(
        self,
        *,
        source_text: str,
        source_language: str,
        target_language: str,
        glossary: dict[str, str] | None = None,
    ) -> TranslationProviderResult:
        messages = _messages(source_text, source_language, target_language, glossary)
        if self._config.provider == "ollama":
            async with OllamaClient(
                base_url=self._config.api_base, model=self._config.model_name
            ) as client:
                response = await client.chat(messages)
        else:
            client_config = LLMConfig(
                provider=self._config.provider,
                model=self._config.model_name,
                api_base=AnyHttpUrl(self._config.api_base),
                api_key=SecretStr(self._api_key or ""),
                timeout_seconds=90,
            )
            async with LLMClient(client_config) as client:
                response = await client.chat(messages)
        try:
            raw = response.text.strip()
            fenced = re.fullmatch(
                r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL | re.IGNORECASE
            )
            payload = json.loads(fenced.group(1) if fenced else raw)
            result = TranslationProviderResult.model_validate(
                {
                    **payload,
                    "provider": response.provider,
                    "model": response.model,
                    "model_revision": payload.get("model_revision", "unknown"),
                }
            )
        except (ValueError, TypeError, ValidationError, AttributeError) as exc:
            raise TemporarilyUnavailableError(
                "Translation model returned invalid structured output"
            ) from exc
        _validate_alignment(result, len(source_text))
        return result


def _messages(
    source: str,
    source_language: str,
    target_language: str,
    glossary: dict[str, str] | None,
) -> list[ChatMessage]:
    system = (
        "You are a conservative medical translator. Preserve every number, comparator, unit, "
        "dose, frequency, negation, uncertainty, group direction, abbreviation and statistical "
        "measure. Do not add claims. Return only JSON with translated_text and alignment. "
        "alignment is an array of source_start/source_end/target_start/target_end integer spans."
    )
    user = json.dumps(
        {
            "source_language": source_language,
            "target_language": target_language,
            "source_text": source,
            "document_glossary": glossary or {},
        },
        ensure_ascii=False,
    )
    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=user),
    ]


def _validate_alignment(result: TranslationProviderResult, source_length: int) -> None:
    target_length = len(result.translated_text)
    covered = [False] * source_length
    for span in result.alignment:
        if span.source_end > source_length or span.target_end > target_length:
            raise TemporarilyUnavailableError(
                "Translation alignment exceeds text bounds"
            )
        for index in range(span.source_start, span.source_end):
            covered[index] = True
    if source_length and sum(covered) / source_length < 0.8:
        raise TemporarilyUnavailableError(
            "Translation alignment coverage is incomplete"
        )


class LocalMarianTranslationProvider:
    """Offline English-to-Chinese Seq2Seq provider for Marian and mBART artifacts.

    The model is loaded lazily and never downloads at request time.  A single
    process-level cache prevents the worker from reloading the several-hundred
    megabyte model for every queued selection.
    """

    _runtime: tuple[Any, Any, Any, str, int | None, str] | None = None
    _runtime_key: tuple[Path, Path | None, str, int] | None = None

    def __init__(
        self,
        model_directory: Path,
        device: str = "auto",
        tokenizer_directory: Path | None = None,
        cpu_threads: int = 2,
    ) -> None:
        self._model_directory = model_directory.resolve()
        self._device = device
        self._tokenizer_directory = (
            tokenizer_directory.resolve() if tokenizer_directory is not None else None
        )
        self._cpu_threads = cpu_threads

    async def translate(
        self,
        *,
        source_text: str,
        source_language: str,
        target_language: str,
        glossary: dict[str, str] | None = None,
    ) -> TranslationProviderResult:
        if (source_language, target_language) != ("en", "zh-CN"):
            raise TemporarilyUnavailableError("Local model supports only en to zh-CN")
        if not source_text.strip() or len(source_text) > 8_000:
            raise TemporarilyUnavailableError("Translation input exceeds local limit")
        translated, provider, raw_alignment = await asyncio.to_thread(
            self._translate_sync, source_text, glossary or {}
        )
        return TranslationProviderResult(
            translated_text=translated,
            alignment=[AlignmentSpan(
                source_start=source_start,
                source_end=source_end,
                target_start=target_start,
                target_end=target_end,
            ) for source_start, source_end, target_start, target_end in raw_alignment],
            provider=provider,
            model=self._model_directory.name,
            model_revision="local-manifest",
        )

    def _translate_sync(
        self, source_text: str, glossary: dict[str, str]
    ) -> tuple[str, str, list[tuple[int, int, int, int]]]:
        tokenizer, model, torch, device, target_token_id, provider = self._load()
        translated_chunks: list[str] = []
        alignment: list[tuple[int, int, int, int]] = []
        target_cursor = 0
        for source_start, source_end in _model_chunks(source_text, tokenizer):
            chunk = source_text[source_start:source_end]
            encoded = tokenizer(
                [chunk], return_tensors="pt", padding=True, truncation=False
            )
            encoded = {name: value.to(device) for name, value in encoded.items()}
            with torch.inference_mode():
                generated = model.generate(
                    **encoded,
                    do_sample=False,
                    num_beams=1,
                    max_new_tokens=512,
                    **(
                        {"forced_bos_token_id": target_token_id}
                        if target_token_id is not None
                        else {}
                    ),
                )
            translated = tokenizer.batch_decode(
                generated, skip_special_tokens=True
            )[0].strip()
            translated = _restore_glossary_terms(chunk, translated, glossary)
            if translated_chunks:
                target_cursor += 1
            target_start = target_cursor
            translated_chunks.append(translated)
            target_cursor += len(translated)
            alignment.append((source_start, source_end, target_start, target_cursor))
        return "\n".join(translated_chunks), provider, alignment

    def _load(self) -> tuple[Any, Any, Any, str, int | None, str]:
        provider_type = type(self)
        runtime_key = (
            self._model_directory,
            self._tokenizer_directory,
            self._device,
            self._cpu_threads,
        )
        if (
            provider_type._runtime is not None
            and provider_type._runtime_key == runtime_key
        ):
            return provider_type._runtime
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise TemporarilyUnavailableError(
                "Local translation runtime is not installed"
            ) from exc
        device = "cuda" if self._device == "cuda" else "cpu"
        if self._device == "auto" and torch.cuda.is_available():
            device = "cuda"
        if device == "cuda" and not torch.cuda.is_available():
            raise TemporarilyUnavailableError("CUDA is not available")
        if device == "cpu":
            torch.set_num_threads(self._cpu_threads)
            try:
                torch.set_num_interop_threads(1)
            except RuntimeError:
                # PyTorch permits this setting only before parallel work starts.
                pass
        tokenizer = AutoTokenizer.from_pretrained(
            self._tokenizer_directory or self._model_directory, local_files_only=True
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(
            self._model_directory, local_files_only=True
        )
        model.to(device)
        model.eval()
        target_token_id: int | None = None
        language_codes = getattr(tokenizer, "lang_code_to_id", {})
        if "en_XX" in language_codes and "zh_CN" in language_codes:
            tokenizer.src_lang = "en_XX"
            target_token_id = int(language_codes["zh_CN"])
        provider = (
            "local-transformers-mbart-paramed"
            if getattr(model.config, "model_type", None) == "mbart"
            else "local-transformers-marian"
        )
        provider_type._runtime = (
            tokenizer,
            model,
            torch,
            device,
            target_token_id,
            provider,
        )
        provider_type._runtime_key = runtime_key
        return provider_type._runtime


def _token_count(tokenizer: Any, text: str) -> int:
    encoded = tokenizer(text, add_special_tokens=True, truncation=False)
    token_ids = encoded["input_ids"]
    if token_ids and isinstance(token_ids[0], list):
        token_ids = token_ids[0]
    return len(token_ids)


def _model_chunks(
    source_text: str, tokenizer: Any, max_input_tokens: int = 480
) -> list[tuple[int, int]]:
    """Return contiguous character spans that never rely on tokenizer truncation."""
    chunks: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(source_text):
        low, high = cursor + 1, len(source_text)
        best = cursor
        while low <= high:
            middle = (low + high) // 2
            if _token_count(tokenizer, source_text[cursor:middle]) <= max_input_tokens:
                best = middle
                low = middle + 1
            else:
                high = middle - 1
        if best == cursor:
            best = cursor + 1
        if best < len(source_text):
            window = source_text[cursor:best]
            boundaries = [match.end() for match in re.finditer(r"(?:[.!?;:]|\s)\s*", window)]
            preferred = next(
                (boundary for boundary in reversed(boundaries) if boundary >= len(window) // 2),
                None,
            )
            if preferred:
                best = cursor + preferred
        chunks.append((cursor, best))
        cursor = best
    return chunks


def _restore_glossary_terms(
    source_text: str, translated_text: str, glossary: dict[str, str]
) -> str:
    """Restore only standalone terms that are present in this exact source chunk."""
    restored = translated_text
    for source_term, target_term in sorted(
        glossary.items(), key=lambda item: len(item[0]), reverse=True
    ):
        term = source_term.strip()
        if not term:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)
        if pattern.search(source_text):
            def replacement(_match: re.Match[str], value: str = target_term) -> str:
                return value

            restored = pattern.sub(replacement, restored)
    return restored


def local_translation_artifact_ready(
    model_directory: Path | None,
    tokenizer_directory: Path | None = None,
) -> bool:
    """Return true only when an offline model and optional tokenizer are usable.

    The separate tokenizer is required by the mBART biomedical artifact.  Marian
    bundles its tokenizer inside the model directory, so it intentionally remains
    optional for that layout.
    """
    if model_directory is None or not (model_directory / "config.json").is_file():
        return False
    if not any(
        (model_directory / filename).is_file()
        for filename in ("model.safetensors", "pytorch_model.bin")
    ):
        return False
    if tokenizer_directory is None:
        return True
    return bool(
        (tokenizer_directory / "tokenizer_config.json").is_file()
        and (tokenizer_directory / "sentencepiece.bpe.model").is_file()
    )
