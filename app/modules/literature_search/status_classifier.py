"""Conservative literature-status classification from verified metadata only."""
from typing import Literal

Status = Literal["normal", "retracted", "corrected", "preprint", "unknown"]
def classify(*, verified: bool, is_retracted: bool = False, is_corrected: bool = False, is_preprint: bool = False) -> Status:
    if not verified: return "unknown"
    if is_retracted: return "retracted"
    if is_corrected: return "corrected"
    if is_preprint: return "preprint"
    return "normal"
