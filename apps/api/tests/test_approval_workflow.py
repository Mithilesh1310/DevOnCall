import pytest
from app.services.agent import StateManager, AgentRuntime

@pytest.mark.asyncio
async def test_human_approval_pause_and_resume():
    run_id = "test-approval-01"
    project_id = "proj-approval-01"
    task = "Fix hello greeting in code"

    state = StateManager.create_initial_state(run_id=run_id, project_id=project_id, user_task=task)
    runtime = AgentRuntime()

    # Initial run should execute steps 0..6 and pause at step 7 awaiting approval
    final_state = await runtime.run(state)
    assert final_state.status == "AWAITING_APPROVAL"
    assert final_state.current_step == 7

    # Resume run after granting human approval
    resumed_state = await runtime.resume_after_approval(final_state)
    assert resumed_state.status == "COMPLETED"
    assert resumed_state.run_context.get("approved") is True

    # Verify PR creation observation
    pr_obs = [obs for obs in resumed_state.observations if obs.tool_name == "create_pull_request"]
    assert len(pr_obs) == 1
    assert pr_obs[0].result.success is True
    assert pr_obs[0].result.data["pr_number"] == 101
