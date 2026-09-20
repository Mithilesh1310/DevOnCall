import pytest
from app.services.agent import AgentRuntime, StateManager
from app.services.agent.planner import MockRepairPlanner
from app.services.agent.policies import default_phase5_policy

@pytest.mark.asyncio
async def test_scenario_a_standard_fix_and_pass():
    state = StateManager.create_initial_state("run-scen-a", "proj-1", "Fix hello greeting function in code")
    planner = MockRepairPlanner(scenario="SCENARIO_A")
    runtime = AgentRuntime(planner=planner, policy=default_phase5_policy)

    final_state = await runtime.run(state)
    assert final_state.status in ["AWAITING_APPROVAL", "COMPLETED"]
    assert len(final_state.tool_calls) >= 2

@pytest.mark.asyncio
async def test_scenario_b_repeated_failure_human_review():
    state = StateManager.create_initial_state("run-scen-b", "proj-1", "Fix repeating test bug")
    planner = MockRepairPlanner(scenario="SCENARIO_B")
    runtime = AgentRuntime(planner=planner, policy=default_phase5_policy)

    final_state = await runtime.run(state)
    assert final_state.status == "AWAITING_APPROVAL"
    assert "human review" in final_state.current_goal.lower()

@pytest.mark.asyncio
async def test_scenario_c_sandbox_blocked_stop():
    state = StateManager.create_initial_state("run-scen-c", "proj-1", "Fix bug on blocked host")
    planner = MockRepairPlanner(scenario="SCENARIO_C")
    runtime = AgentRuntime(planner=planner, policy=default_phase5_policy)

    final_state = await runtime.run(state)
    assert final_state.status in ["COMPLETED", "FAILED"]
    assert "blocked" in final_state.current_goal.lower() or "stopping" in final_state.current_goal.lower()

@pytest.mark.asyncio
async def test_scenario_d_typecheck_and_test():
    state = StateManager.create_initial_state("run-scen-d", "proj-1", "Fix TypeScript compilation error")
    planner = MockRepairPlanner(scenario="SCENARIO_D")
    runtime = AgentRuntime(planner=planner, policy=default_phase5_policy)

    final_state = await runtime.run(state)
    assert final_state.status == "COMPLETED"
    assert len(final_state.tool_calls) >= 3
