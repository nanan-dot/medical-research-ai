from app.agents.state import AgentState


def test_state_round_trip_and_step_limit():
    state = AgentState("q", max_steps=1)
    assert state.advance() and not state.advance()
    assert AgentState.restore(state.serialize()).user_query == "q"
