"""Legal parse and index task state transitions."""

from enum import StrEnum

from app.common.exceptions import ConflictError
from app.modules.document.schema import IndexStatus, ParseStatus

PARSE_TRANSITIONS: dict[ParseStatus, frozenset[ParseStatus]] = {
    ParseStatus.PENDING: frozenset({ParseStatus.PARSING}),
    ParseStatus.PARSING: frozenset({ParseStatus.SUCCEEDED, ParseStatus.FAILED}),
    ParseStatus.SUCCEEDED: frozenset({ParseStatus.PENDING}),
    ParseStatus.FAILED: frozenset({ParseStatus.PENDING}),
}

INDEX_TRANSITIONS: dict[IndexStatus, frozenset[IndexStatus]] = {
    IndexStatus.PENDING: frozenset({IndexStatus.INDEXING}),
    IndexStatus.INDEXING: frozenset(
        {IndexStatus.SUCCEEDED, IndexStatus.FAILED, IndexStatus.OUTDATED}
    ),
    IndexStatus.SUCCEEDED: frozenset({IndexStatus.PENDING, IndexStatus.OUTDATED}),
    IndexStatus.FAILED: frozenset({IndexStatus.PENDING}),
    IndexStatus.OUTDATED: frozenset({IndexStatus.PENDING}),
}


def ensure_transition[State: StrEnum](
    current: State,
    target: State,
    transitions: dict[State, frozenset[State]],
    task_name: str,
) -> None:
    if target not in transitions[current]:
        raise ConflictError(
            f"Illegal {task_name} state transition: {current.value} -> {target.value}"
        )


def ensure_parse_transition(current: ParseStatus, target: ParseStatus) -> None:
    ensure_transition(current, target, PARSE_TRANSITIONS, "parse")


def ensure_index_transition(current: IndexStatus, target: IndexStatus) -> None:
    ensure_transition(current, target, INDEX_TRANSITIONS, "index")
