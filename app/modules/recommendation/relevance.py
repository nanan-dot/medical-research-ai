"""Field-aware structured-intent relevance scoring."""

from app.modules.literature_search.schema import CitationItem
from app.modules.recommendation.scoring import FEATURE_SCHEMA_VERSION


def _values(raw: object) -> list[str]:
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(value) for value in raw if value]
    return []


def score_relevance(
    item: CitationItem, dimensions: dict[str, object]
) -> tuple[float | None, list[dict[str, object]], list[str]]:
    fields: dict[str, tuple[str, float]] = {
        "pubmed_title": ((item.title or "").casefold(), 0.35),
        "pubmed_abstract_results": ((item.abstract or "").casefold(), 0.30),
        "pubmed_mesh": (" ".join(item.mesh_terms).casefold(), 0.20),
        "pubmed_publication_type": (
            " ".join(item.publication_types).casefold(),
            0.15,
        ),
    }
    dimension_weights = {
        "disease": 0.18,
        "population": 0.12,
        "intervention": 0.15,
        "comparison": 0.08,
        "outcome": 0.15,
        "target": 0.10,
        "mechanism": 0.08,
        "study_type": 0.08,
        "mesh": 0.06,
    }
    matches: list[dict[str, object]] = []
    dimension_scores: list[tuple[float, float]] = []
    sources: set[str] = set()
    for dimension, dimension_weight in dimension_weights.items():
        terms = _values(dimensions.get(dimension))
        if not terms:
            continue
        normalized_terms = sorted({term.casefold(): term for term in terms}.items())
        available_fields = [
            (source, text, weight) for source, (text, weight) in fields.items() if text
        ]
        if not available_fields:
            matches.append(
                {
                    "dimension": dimension,
                    "status": "unavailable",
                    "matched_terms": [],
                    "source": "intent_snapshot",
                    "field": "pubmed_metadata",
                    "reason": "candidate_has_no_scorable_pubmed_fields",
                    "version": FEATURE_SCHEMA_VERSION,
                }
            )
            continue
        hits: set[str] = set()
        hit_fields: list[str] = []
        field_numerator = 0.0
        field_denominator = 0.0
        for source, text, field_weight in available_fields:
            field_hits = [
                original
                for normalized, original in normalized_terms
                if normalized in text
            ]
            field_numerator += field_weight * (len(field_hits) / len(normalized_terms))
            field_denominator += field_weight
            if field_hits:
                hits.update(field_hits)
                hit_fields.append(source)
                sources.add(source)
        score = field_numerator / field_denominator
        dimension_scores.append((score, dimension_weight))
        matches.append(
            {
                "dimension": dimension,
                "status": "matched" if hits else "available_no_match",
                "matched_terms": sorted(hits),
                "source": "intent_snapshot",
                "field": ",".join(sorted(set(hit_fields))) or "pubmed_metadata",
                "reason": "weighted_structured_intent_lexical_match",
                "version": FEATURE_SCHEMA_VERSION,
            }
        )
    denominator = sum(weight for _, weight in dimension_scores)
    final_score = (
        round(
            sum(value * weight for value, weight in dimension_scores) / denominator,
            6,
        )
        if denominator
        else None
    )
    return final_score, matches, sorted(sources)
