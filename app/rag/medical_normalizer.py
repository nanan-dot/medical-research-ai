"""Deterministic medical-text normalization that preserves clinical relations."""

from __future__ import annotations

import re
from dataclasses import dataclass

NORMALIZER_VERSION = "medical-normalizer-v1"
_VARIANT_PATTERN = re.compile(r"\b(?:KRAS\s+G12C|EGFR\s+T790M|c\.\d+[A-Za-z]>[A-Za-z])\b", re.IGNORECASE)
_TOKEN_PATTERN = re.compile(r"PD-L1|HER2[+-]|TPS|≥|<=|≥|>|<|\d+(?:\.\d+)?|%|[A-Za-z][A-Za-z0-9-]*", re.IGNORECASE)
_CHINESE_RUN_PATTERN = re.compile(r"[\u4e00-\u9fff]+")


@dataclass(frozen=True)
class NormalizedMedicalText:
    raw_text: str
    tokens: frozenset[str]
    version: str = NORMALIZER_VERSION


def normalize_medical_text(text: str) -> NormalizedMedicalText:
    """Return versioned tokens while retaining the caller's original text intact."""
    variants = {match.group(0).casefold().replace(" ", "_") for match in _VARIANT_PATTERN.finditer(text)}
    protected = _VARIANT_PATTERN.sub(lambda match: match.group(0).replace(" ", "_"), text)
    tokens = {token.casefold() for token in _TOKEN_PATTERN.findall(protected)}
    for run in _CHINESE_RUN_PATTERN.findall(text):
        tokens.update(run[index : index + 2] for index in range(max(0, len(run) - 1)))
        if len(run) == 1:
            tokens.add(run)
    return NormalizedMedicalText(raw_text=text, tokens=frozenset(tokens | variants))
