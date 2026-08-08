"""Presentation contract tests that require no external model or network."""

import pytest
from pydantic import ValidationError

from app.modules.presentation.schema import OutlineSection, PresentationCreate


def test_outline_section_marks_missing_evidence_explicitly() -> None:
    section = OutlineSection(
        title="Figures to review",
        content="Figures were not parsed; inspect the original paper.",
        missing_evidence=True,
    )

    assert section.evidence == []
    assert section.missing_evidence is True


def test_presentation_requires_at_least_one_document() -> None:
    with pytest.raises(ValidationError):
        PresentationCreate(document_ids=[])
