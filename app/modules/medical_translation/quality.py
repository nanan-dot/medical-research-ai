"""Deterministic checks for facts that must survive medical translation."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QualityIssue:
    code: str
    severity: str
    blocking: bool
    message: str
    source_span: tuple[int, int] | None = None
    target_span: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class TermEvidence:
    source_term: str
    target_term: str | None
    status: str
    provenance: str
    version: str = "phase1-local-terms-v1"
    authority: str | None = None
    source_span: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class QualityReport:
    issues: tuple[QualityIssue, ...]
    terms: tuple[TermEvidence, ...]
    blocked: bool
    quality_status: str


_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?%?")
_COMPARATOR = re.compile(r"(?:<=|>=|<|>|≤|≥)")
_EFFECT = re.compile(r"\b(?:HR|RR|OR)\b", re.IGNORECASE)
_INTERVAL = re.compile(r"\b\d+(?:\.\d+)?%?\s*[-–—]\s*\d+(?:\.\d+)?%?")
_DOSE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|μg|ug|mL|ml|IU)\b", re.IGNORECASE)
_ABBREVIATION = re.compile(r"\b[A-Z][A-Z0-9-]{1,9}\b")
_KNOWN_TERMS = {"HR", "RR", "OR", "CI", "P", "ML", "IU"}


def _span(pattern: re.Pattern[str], value: str) -> tuple[int, int] | None:
    match = pattern.search(value)
    return match.span() if match else None


def _tokens(pattern: re.Pattern[str], value: str) -> Counter[str]:
    return Counter(
        match.group(0).lower().replace("μ", "u") for match in pattern.finditer(value)
    )


def _issue(
    code: str, message: str, source: str, target: str, pattern: re.Pattern[str]
) -> QualityIssue:
    return QualityIssue(
        code=code,
        severity="critical"
        if code in {"DOSE_MISMATCH", "NEGATION_MISSING"}
        else "error",
        blocking=True,
        message=message,
        source_span=_span(pattern, source),
        target_span=_span(pattern, target),
    )


def _has_degenerate_repetition(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    if len(compact) < 40:
        return False
    for width in range(1, min(16, len(compact) // 5) + 1):
        counts = Counter(
            compact[index:index + width]
            for index in range(0, len(compact) - width + 1, width)
        )
        highest = max(counts.values(), default=0)
        if highest >= 5 and highest * width >= len(compact) * 0.55:
            return True
    return False


def validate_translation(source: str, target: str) -> QualityReport:
    issues: list[QualityIssue] = []
    if "\ufffd" in target:
        issues.append(
            QualityIssue(
                "INVALID_UNICODE_OUTPUT",
                "critical",
                True,
                "译文包含无效字符，模型输出不可用",
                (0, len(source)),
                (target.index("\ufffd"), target.index("\ufffd") + 1),
            )
        )
    if _has_degenerate_repetition(target):
        issues.append(
            QualityIssue(
                "DEGENERATE_REPETITION",
                "critical",
                True,
                "译文出现异常重复循环，模型输出不可用",
                (0, len(source)),
                (0, len(target)),
            )
        )
    if _tokens(_NUMBER, source) != _tokens(_NUMBER, target):
        issues.append(
            _issue(
                "NUMBER_MISMATCH", "数字或百分比未被完整保留", source, target, _NUMBER
            )
        )
    if _tokens(_COMPARATOR, source) != _tokens(_COMPARATOR, target):
        issues.append(
            _issue(
                "COMPARATOR_MISMATCH", "比较符号发生变化", source, target, _COMPARATOR
            )
        )
    if _tokens(_INTERVAL, source) != _tokens(_INTERVAL, target):
        issues.append(
            _issue(
                "INTERVAL_MISMATCH",
                "区间或置信区间端点发生变化",
                source,
                target,
                _INTERVAL,
            )
        )
    if _tokens(_EFFECT, source) != _tokens(_EFFECT, target):
        issues.append(
            _issue(
                "EFFECT_MEASURE_MISMATCH", "效应量类型发生变化", source, target, _EFFECT
            )
        )
    if _tokens(_DOSE, source) != _tokens(_DOSE, target):
        issues.append(
            _issue("DOSE_MISMATCH", "剂量或单位发生变化", source, target, _DOSE)
        )

    source_lower = source.lower()
    target_lower = target.lower()
    source_negative = bool(
        re.search(r"\b(?:not|no|without|neither|never)\b", source_lower)
    )
    target_negative = bool(
        re.search(r"(?:不|无|未|非|没有|并不|not|no|without)", target_lower)
    )
    if source_negative and not target_negative:
        issues.append(
            _issue(
                "NEGATION_MISSING",
                "原文否定语义未保留",
                source,
                target,
                re.compile(r"\b(?:not|no|without|neither|never)\b", re.IGNORECASE),
            )
        )

    source_higher = bool(
        re.search(r"\b(?:higher|greater|increased|above)\b", source_lower)
    )
    source_lower_direction = bool(
        re.search(r"\b(?:lower|less|decreased|below)\b", source_lower)
    )
    target_higher = bool(
        re.search(r"(?:高于|更高|增加|上升|higher|greater)", target_lower)
    )
    target_lower_direction = bool(
        re.search(r"(?:低于|更低|减少|下降|lower|less)", target_lower)
    )
    if (source_higher and target_lower_direction) or (
        source_lower_direction and target_higher
    ):
        issues.append(
            _issue(
                "DIRECTION_MISMATCH",
                "组间比较方向发生反转",
                source,
                target,
                re.compile(
                    r"\b(?:higher|greater|increased|above|lower|less|decreased|below)\b",
                    re.IGNORECASE,
                ),
            )
        )

    if not target.strip():
        issues.append(
            QualityIssue(
                "EMPTY_TRANSLATION",
                "critical",
                True,
                "译文为空",
                (0, len(source)),
                None,
            )
        )
    elif len(target.strip()) < max(1, len(source.strip()) // 12):
        issues.append(
            QualityIssue(
                "COVERAGE_TOO_LOW",
                "error",
                True,
                "译文覆盖率过低",
                (0, len(source)),
                (0, len(target)),
            )
        )

    terms = tuple(
        TermEvidence(
            source_term=match.group(0),
            target_term=match.group(0) if match.group(0) in _KNOWN_TERMS else None,
            status="matched" if match.group(0) in _KNOWN_TERMS else "unresolved",
            provenance="phase1-local-rule",
            source_span=match.span(),
        )
        for match in _ABBREVIATION.finditer(source)
    )
    blocked = any(issue.blocking for issue in issues)
    quality_status = (
        "blocked"
        if blocked
        else (
            "needs_review"
            if any(term.status != "matched" for term in terms)
            else "machine_checked"
        )
    )
    return QualityReport(tuple(issues), terms, blocked, quality_status)
