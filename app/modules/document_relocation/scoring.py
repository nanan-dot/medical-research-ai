"""Pure deterministic evidence scoring for A3 relocation candidates."""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.modules.document_anchor.normalization import normalize_text_item

_PROTECTED_PATTERN = re.compile(
    r"(?ix)\b(?:"
    r"\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?%?"
    r"|HR|RR|OR|CI|P"
    r"|mg|mcg|μg|g|kg|ml|mmol|days?|weeks?|months?|years?"
    r"|no|not|without|increase(?:d)?|decrease(?:d)?|higher|lower"
    r")\b"
)


@dataclass(frozen=True)
class ProtectedTokenComparison:
    status: str
    missing: tuple[str, ...]
    added: tuple[str, ...]


@dataclass(frozen=True)
class CandidateScore:
    breakdown: dict[str, float]
    protected_token_status: str
    is_eligible: bool


def _protected_tokens(text: str) -> tuple[str, ...]:
    return tuple(
        match.group(0).casefold() for match in _PROTECTED_PATTERN.finditer(text)
    )


def compare_protected_tokens(source: str, candidate: str) -> ProtectedTokenComparison:
    """Compare safety-critical literal expressions without exposing source text."""
    source_tokens = _protected_tokens(source)
    candidate_tokens = _protected_tokens(candidate)
    missing = tuple(token for token in source_tokens if token not in candidate_tokens)
    added = tuple(token for token in candidate_tokens if token not in source_tokens)
    return ProtectedTokenComparison(
        status="match" if source_tokens == candidate_tokens else "mismatch",
        missing=missing,
        added=added,
    )


def score_candidate(
    source: str,
    candidate: str,
    *,
    prefix_similarity: float = 0.0,
    suffix_similarity: float = 0.0,
    section_similarity: float = 0.0,
    position_similarity: float = 0.0,
    geometry_similarity: float = 0.0,
) -> CandidateScore:
    """Return auditable numeric evidence; the score never confirms a candidate."""
    source_normalized = normalize_text_item(source).normalized_text
    candidate_normalized = normalize_text_item(candidate).normalized_text
    protected = compare_protected_tokens(source, candidate)
    exactness = (
        1.0
        if source_normalized == candidate_normalized
        else SequenceMatcher(None, source_normalized, candidate_normalized).ratio()
    )
    context_similarity = (prefix_similarity + suffix_similarity) / 2
    breakdown = {
        "quote_exactness": round(exactness, 6),
        "context_similarity": round(context_similarity, 6),
        "protected_token_match": 1.0 if protected.status == "match" else 0.0,
        "section_path_match": round(section_similarity, 6),
        "relative_position_consistency": round(position_similarity, 6),
        "geometry_consistency": round(geometry_similarity, 6),
    }
    return CandidateScore(
        breakdown=breakdown,
        protected_token_status=protected.status,
        is_eligible=exactness >= 0.6 and protected.status == "match",
    )


__all__ = [
    "CandidateScore",
    "ProtectedTokenComparison",
    "compare_protected_tokens",
    "score_candidate",
]
