"""Optional local scispaCy adapter; never downloads models at runtime."""
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any


@dataclass(frozen=True)
class MedicalEntity:
    text: str; label: str; normalized_id: str | None = None; confidence: float | None = None

class SciSpacyClient:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._nlp: Any = None  # 延迟加载的 spacy 管道；类型为 Any 避免 mypy 将 None 视为不可调用
    @property
    def available(self) -> bool: return find_spec("scispacy") is not None and find_spec("spacy") is not None
    def extract(self, text: str) -> list[MedicalEntity]:
        if not self.available: return []
        if self._nlp is None:
            import spacy
            try: self._nlp = spacy.load(self._model_name)
            except OSError: return []
        return [MedicalEntity(entity.text, entity.label_) for entity in self._nlp(text).ents]
