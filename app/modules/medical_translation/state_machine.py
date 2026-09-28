"""Small explicit state machine shared by API and workers."""

from typing import Literal

TranslationState = Literal[
    "queued", "running", "quality_checking", "succeeded", "failed", "cancelled"
]
TERMINAL_STATES = frozenset({"succeeded", "failed", "cancelled"})
_ALLOWED: dict[str, frozenset[str]] = {
    "queued": frozenset({"running", "cancelled"}),
    "running": frozenset({"quality_checking", "failed", "cancelled"}),
    "quality_checking": frozenset({"succeeded", "failed", "cancelled"}),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}


class InvalidTranslationTransition(ValueError):
    pass


def transition(current: str, target: str) -> TranslationState:
    if target not in _ALLOWED.get(current, frozenset()):
        raise InvalidTranslationTransition(f"illegal transition: {current} -> {target}")
    return target  # type: ignore[return-value]
