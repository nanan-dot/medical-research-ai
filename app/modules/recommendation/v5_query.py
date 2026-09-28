"""Auditable PubMed query construction from a confirmed intent snapshot."""

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryTerm:
    value: str
    dimension: str
    source: str
    field: str


@dataclass(frozen=True)
class AuditableQuery:
    query: str
    terms: list[QueryTerm]


def build_intent_query(dimensions: dict[str, object]) -> AuditableQuery:
    return build_intent_query_variants(dimensions)[0]


def build_intent_query_variants(dimensions: dict[str, object]) -> list[AuditableQuery]:
    terms: list[QueryTerm] = []
    groups: list[tuple[str, str]] = []
    for dimension in (
        "disease",
        "population",
        "intervention",
        "comparison",
        "outcome",
        "target",
        "mechanism",
        "study_type",
        "mesh",
    ):
        raw = dimensions.get(dimension)
        values = raw if isinstance(raw, list) else [raw] if isinstance(raw, str) else []
        clean = [str(value).strip() for value in values if str(value).strip()]
        if not clean:
            continue
        field = "MeSH Terms" if dimension == "mesh" else "Title/Abstract"
        groups.append((dimension, "(" + " OR ".join(f'"{value}"[{field}]' for value in clean) + ")"))
        terms.extend(
            QueryTerm(value, dimension, "intent_snapshot", field) for value in clean
        )
    if not groups:
        raise ValueError("confirmed intent contains no searchable concepts")
    strict = AuditableQuery(" AND ".join(group for _, group in groups) + " NOT retracted publication[pt]", terms)
    variants = [strict]
    optional_dimensions = ("outcome", "comparison", "mechanism", "target", "study_type", "population", "mesh")
    retained = groups[:]
    for dimension in optional_dimensions:
        narrowed = [entry for entry in retained if entry[0] != dimension]
        if len(narrowed) < 1 or len(narrowed) == len(retained):
            continue
        retained = narrowed
        variants.append(AuditableQuery(" AND ".join(group for _, group in retained) + " NOT retracted publication[pt]", terms))
    return variants
