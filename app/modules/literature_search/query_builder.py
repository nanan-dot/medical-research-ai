"""Safe, explainable PubMed boolean-query construction."""

from __future__ import annotations

import re

from app.modules.literature_search.schema import BooleanQueryResult, SearchTermGroup

_ILLEGAL = re.compile(r"[{};\n\r]")
_PUBMED_TERM = re.compile(r"^[\x20-\x7e]+$")


def validate_term(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned or _ILLEGAL.search(cleaned) or not _PUBMED_TERM.fullmatch(cleaned):
        raise ValueError(
            "terms must be non-empty ASCII PubMed terms without braces, semicolons, or newlines"
        )
    return cleaned


def build_boolean_query(groups: list[SearchTermGroup]) -> BooleanQueryResult:
    clauses: list[str] = []
    explanations: list[str] = []
    field_tags: dict[str, str] = {}
    for group in groups:
        terms = [validate_term(term) for term in group.terms]
        if not terms:
            continue
        tag = group.field_tag or "Title/Abstract"
        field_tags[group.name] = tag
        terms_clause = " OR ".join(f'"{term}"[{tag}]' for term in dict.fromkeys(terms))
        clauses.append(f"({terms_clause})")
        explanations.append(
            f"{group.name}: OR keeps equivalent terms within one concept group."
        )
    if not clauses:
        raise ValueError("at least one non-empty term group is required")
    return BooleanQueryResult(
        boolean_query=" AND ".join(clauses),
        field_tags=field_tags,
        explanations=explanations
        + ["AND connects different concepts so all selected concepts are required."],
    )
