import pytest

from app.common.exceptions import ConflictError
from app.modules.document.schema import IndexStatus, ParseStatus
from app.modules.document.state_machine import ensure_index_transition, ensure_parse_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ParseStatus.PENDING, ParseStatus.PARSING),
        (ParseStatus.PARSING, ParseStatus.SUCCEEDED),
        (ParseStatus.PARSING, ParseStatus.FAILED),
        (ParseStatus.FAILED, ParseStatus.PENDING),
    ],
)
def test_legal_parse_transitions(current, target):
    ensure_parse_transition(current, target)


def test_illegal_parse_transition_is_conflict():
    with pytest.raises(ConflictError, match="pending -> succeeded"):
        ensure_parse_transition(ParseStatus.PENDING, ParseStatus.SUCCEEDED)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (IndexStatus.PENDING, IndexStatus.INDEXING),
        (IndexStatus.INDEXING, IndexStatus.SUCCEEDED),
        (IndexStatus.INDEXING, IndexStatus.FAILED),
        (IndexStatus.SUCCEEDED, IndexStatus.OUTDATED),
        (IndexStatus.OUTDATED, IndexStatus.PENDING),
    ],
)
def test_legal_index_transitions(current, target):
    ensure_index_transition(current, target)


def test_illegal_index_transition_is_conflict():
    with pytest.raises(ConflictError, match="pending -> succeeded"):
        ensure_index_transition(IndexStatus.PENDING, IndexStatus.SUCCEEDED)
