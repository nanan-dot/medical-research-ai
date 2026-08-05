"""Exact, evidence-backed identifiers used to associate local documents with literature."""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.modules.document.model import Document

_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:a-z0-9]+", re.IGNORECASE)
_PMID_PATTERN = re.compile(r"\bPMID\s*[:#]?\s*(\d{1,20})\b", re.IGNORECASE)


def normalize_doi(value: str | None) -> str | None:
    """Normalize only DOI presentation variants; invalid values remain unmatched."""
    if not value:
        return None
    candidate = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix) :].strip()
    return candidate if _DOI_PATTERN.fullmatch(candidate) else None


def find_exact_document_match(
    documents: Iterable[Document], *, pmid: str, doi: str | None
) -> Document | None:
    """Return one local document only when parsed text has the exact PMID or DOI.

    Title similarity is deliberately excluded: a wrong PDF is worse than no automatic link.
    """
    normalized_doi = normalize_doi(doi)
    for document in documents:
        content = document.parsed_content or ""
        if any(match == pmid for match in _PMID_PATTERN.findall(content)):
            return document
        if normalized_doi and normalized_doi in {
            normalize_doi(match) for match in _DOI_PATTERN.findall(content)
        }:
            return document
    return None
