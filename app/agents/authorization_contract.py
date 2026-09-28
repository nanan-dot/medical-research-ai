"""Frozen authorization vocabulary shared by API and model gateway."""

from enum import StrEnum


class ContentGranularity(StrEnum):
    METADATA = "metadata"
    SELECTION = "selection"
    SECTION = "section"
    FULLTEXT = "fulltext"


class DataCategory(StrEnum):
    SEARCH_QUERY = "search_query"
    BIBLIOGRAPHIC_METADATA = "bibliographic_metadata"
    DOCUMENT_TEXT = "document_text"
    CONFIRMED_EVIDENCE = "confirmed_evidence"
    USER_JUDGEMENT = "user_judgement"
    PRIVATE_NOTE = "private_note"
    RESEARCH_CONTEXT = "research_context"
    STUDY_DESIGN = "study_design"
    MANUSCRIPT_DRAFT = "manuscript_draft"
    AUTHOR_DECLARATION = "author_declaration"


def normalize_authorization_scope(
    content_granularity: str | ContentGranularity,
    data_categories: tuple[str | DataCategory, ...] | list[str | DataCategory],
) -> tuple[str, tuple[str, ...]]:
    """Reject vocabulary drift at every non-HTTP service boundary."""
    granularity = ContentGranularity(content_granularity).value
    categories = tuple(sorted({DataCategory(item).value for item in data_categories}))
    if not categories:
        raise ValueError("at least one data category is required")
    return granularity, categories
