"""A3.1 additive schema acceptance checks."""

from app.core import models  # noqa: F401 - registers every model on Base.metadata
from app.core.database import Base


def test_a3_additive_tables_keep_original_and_resolved_anchor_separate() -> None:
    """A confirmed relocation may resolve an asset but can never rewrite its origin."""
    from app.modules.document_relocation.model import (
        AssetAnchorLink,
        DocumentAnchorRelocation,
        DocumentFileRevision,
        LegacyAnchorBackfillItem,
        LegacyAnchorBackfillRun,
    )

    names = set(Base.metadata.tables)
    assert {
        DocumentFileRevision.__tablename__,
        DocumentAnchorRelocation.__tablename__,
        AssetAnchorLink.__tablename__,
        LegacyAnchorBackfillRun.__tablename__,
        LegacyAnchorBackfillItem.__tablename__,
    } <= names
    link_columns = set(
        Base.metadata.tables[AssetAnchorLink.__tablename__].columns.keys()
    )
    assert {
        "original_anchor_id",
        "resolved_anchor_id",
        "resolution_status",
        "resolution_version",
    } <= link_columns
