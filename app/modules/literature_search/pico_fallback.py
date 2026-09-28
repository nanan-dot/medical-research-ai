"""Deterministic fallback extraction for curated Chinese PICO phrases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PicoFallback:
    """Known PICO fragments copied from the user's question without translation."""

    population: str | None = None
    intervention: str | None = None
    comparison: str | None = None
    outcome: str | None = None


def extract_curated_pico(raw_topic: str) -> PicoFallback:
    """Extract only explicitly curated phrases so fallback data stays auditable."""
    compact_topic = "".join(raw_topic.split())
    population = _extract_population(compact_topic)
    intervention = _extract_first_phrase(
        compact_topic, "新辅助免疫治疗", "抗纤维化药物"
    )
    comparison = _extract_phrase(compact_topic, "标准新辅助放化疗")
    outcome = _extract_outcomes(compact_topic)
    return PicoFallback(population, intervention, comparison, outcome)


def _extract_population(compact_topic: str) -> str | None:
    if "局部晚期直肠癌患者" in compact_topic:
        return "局部晚期直肠癌患者"
    if "间质性肺疾病" in compact_topic:
        return "间质性肺疾病患者" if "患者" in compact_topic else "间质性肺疾病"
    return _extract_phrase(compact_topic, "局部晚期直肠癌")


def _extract_phrase(compact_topic: str, phrase: str) -> str | None:
    return phrase if phrase in compact_topic else None


def _extract_first_phrase(compact_topic: str, *phrases: str) -> str | None:
    return next((phrase for phrase in phrases if phrase in compact_topic), None)


def _extract_outcomes(compact_topic: str) -> str | None:
    if "疗效与安全性" in compact_topic:
        return "疗效与安全性"
    phrases = [
        phrase
        for phrase in ("病理完全缓解率", "≥3级治疗相关不良事件")
        if phrase in compact_topic
    ]
    return "；".join(phrases) or None
