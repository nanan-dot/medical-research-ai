"""证据写作流程状态机。"""

from typing import Literal

WorkflowState = Literal[
    "drafting", "outline_pending", "outline_confirmed", "user_editing", "polishing", "done"
]

_TRANSITIONS: dict[tuple[WorkflowState, str], WorkflowState] = {
    ("drafting", "submit_outline"): "outline_pending",
    ("outline_pending", "confirm_outline"): "outline_confirmed",
    ("outline_confirmed", "generate_draft"): "drafting",
    ("drafting", "start_editing"): "user_editing",
    ("user_editing", "start_polishing"): "polishing",
    ("polishing", "finish"): "done",
}


def transition(state: WorkflowState, action: str) -> WorkflowState:
    try:
        return _TRANSITIONS[(state, action)]
    except KeyError as error:
        raise ValueError(f"Illegal writing workflow transition: {state} + {action}") from error
