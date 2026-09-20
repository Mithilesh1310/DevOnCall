import pytest
from app.services.agent.runtime import AgentRuntime, MAX_AGENT_ITERATIONS
from app.services.agent.state import StateManager

@pytest.mark.asyncio
async def test_agent_runtime_successful_execution_loop():
    runtime = AgentRuntime()
    state = StateManager.create_initial_state("run-loop-1", "proj-loop-1", "Understand this repository")
    
    mock_snapshot = {
        "owner": "mock-owner",
        "repo": "devoncall-demo",
        "default_branch": "main",
        "commit_sha": "a1b2c3d4",
        "url": "https://github.com/mock-owner/devoncall-demo",
        "tree": [{"path": "README.md", "type": "file"}]
    }

    final_state = await runtime.run(state, repository_snapshot=mock_snapshot)

    assert final_state.status == "COMPLETED"
    assert len(final_state.tool_calls) == 3
    assert final_state.iteration_count == 3
    assert final_state.tool_calls[0].tool_name == "repository_info"
    assert final_state.tool_calls[1].tool_name == "repository_tree"
    assert final_state.tool_calls[2].tool_name == "project_snapshot"

@pytest.mark.asyncio
async def test_agent_runtime_max_iterations_limit():
    runtime = AgentRuntime()
    state = StateManager.create_initial_state("run-limit-1", "proj-limit-1", "Infinite task")
    state.iteration_count = MAX_AGENT_ITERATIONS

    final_state = await runtime.run(state)
    assert final_state.status == "FAILED"
    assert any("maximum iteration limit" in err for err in final_state.errors)
