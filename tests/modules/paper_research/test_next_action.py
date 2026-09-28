"""AC-PCB-06 deterministic action-rule coverage."""

from app.modules.paper_research.next_action import decide_next_action


def test_next_action_priority_and_fallbacks_are_explicit():
    assert (
        decide_next_action(
            pending_fields=1,
            analysis_status="analyzing",
            reading_status="reading",
            can_read=True,
            can_analyze=True,
            reader_target=None,
            section=None,
            item_id=1,
        ).kind
        == "confirm_analysis"
    )
    assert (
        decide_next_action(
            pending_fields=0,
            analysis_status="pending",
            reading_status="reading",
            can_read=True,
            can_analyze=True,
            reader_target=None,
            section=None,
            item_id=1,
        ).kind
        == "continue_analysis"
    )
    exact = decide_next_action(
        pending_fields=0,
        analysis_status="succeeded",
        reading_status="reading",
        can_read=True,
        can_analyze=True,
        reader_target={"page": 4},
        section=None,
        item_id=1,
    )
    assert exact.kind == "continue_reading" and exact.target == {"page": 4}
    fallback = decide_next_action(
        pending_fields=0,
        analysis_status="succeeded",
        reading_status="reading",
        can_read=True,
        can_analyze=True,
        reader_target=None,
        section="Methods",
        item_id=1,
    )
    assert fallback.target == {"item_id": 1, "section": "Methods"}
    unavailable = decide_next_action(
        pending_fields=0,
        analysis_status="succeeded",
        reading_status="reading",
        can_read=False,
        can_analyze=False,
        reader_target=None,
        section=None,
        item_id=1,
    )
    assert (
        not unavailable.is_available
        and unavailable.unavailable_reason == "reader_unavailable"
    )


def test_next_action_start_and_terminal_branches_are_deterministic():
    reading = decide_next_action(
        pending_fields=0,
        analysis_status=None,
        reading_status="unread",
        can_read=True,
        can_analyze=True,
        reader_target=None,
        section=None,
        item_id=2,
    )
    analysis = decide_next_action(
        pending_fields=0,
        analysis_status=None,
        reading_status="read",
        can_read=False,
        can_analyze=True,
        reader_target=None,
        section=None,
        item_id=2,
    )
    terminal = decide_next_action(
        pending_fields=0,
        analysis_status="failed",
        reading_status="read",
        can_read=False,
        can_analyze=False,
        reader_target=None,
        section=None,
        item_id=2,
    )
    assert reading.kind == "start_reading"
    assert analysis.kind == "start_analysis"
    assert terminal.kind == "unavailable" and not terminal.is_available
