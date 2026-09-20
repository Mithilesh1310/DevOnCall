import pytest
from app.services.agent.state import StateManager
from app.services.agent.models import AgentState

def test_agent_state_creation_and_serialization():
    state = StateManager.create_initial_state(
        run_id="run-101",
        project_id="proj-202",
        user_task="Understand this repository structure"
    )

    assert state.run_id == "run-101"
    assert state.project_id == "proj-202"
    assert state.user_task == "Understand this repository structure"
    assert state.status == "PENDING"
    assert state.current_step == 0
    assert state.iteration_count == 0

    state_dict = state.model_dump(mode="json")
    assert state_dict["run_id"] == "run-101"
    assert isinstance(state_dict["created_at"], str)
