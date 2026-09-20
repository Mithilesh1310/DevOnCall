import pytest
from app.services.agent.planner import MockPlanner
from app.services.agent.state import StateManager

def test_mock_planner_deterministic_sequence():
    planner = MockPlanner()
    state = StateManager.create_initial_state("run-1", "proj-1", "Understand this repository")

    tools = ["repository_info", "repository_tree", "project_snapshot"]

    # Step 0
    state.current_step = 0
    act0 = planner.plan(state, tools)
    assert act0.action_type == "tool_call"
    assert act0.tool == "repository_info"

    # Step 1
    state.current_step = 1
    act1 = planner.plan(state, tools)
    assert act1.action_type == "tool_call"
    assert act1.tool == "repository_tree"

    # Step 2
    state.current_step = 2
    act2 = planner.plan(state, tools)
    assert act2.action_type == "tool_call"
    assert act2.tool == "project_snapshot"

    # Step 3
    state.current_step = 3
    act3 = planner.plan(state, tools)
    assert act3.completed is True
