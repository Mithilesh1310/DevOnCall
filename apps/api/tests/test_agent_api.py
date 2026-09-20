import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_agent_run_create_and_query_flow(client: AsyncClient):
    # 1. Create Project
    proj_resp = await client.post("/api/v1/projects", json={
        "name": "Agent Test Workspace",
        "github_owner": "mock-owner",
        "github_repo": "devoncall-demo"
    })
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Inspect project to build snapshot
    await client.post(f"/api/v1/projects/{project_id}/github/inspect")

    # 3. Create & Run Agent Task
    agent_resp = await client.post("/api/v1/agent/runs", json={
        "project_id": project_id,
        "task": "Understand this repository structure"
    })
    assert agent_resp.status_code == 201
    run_data = agent_resp.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["user_task"] == "Understand this repository structure"
    assert len(run_data["tool_calls"]) == 3

    run_id = run_data["id"]

    # 4. Query Agent Run details
    query_resp = await client.get(f"/api/v1/agent/runs/{run_id}")
    assert query_resp.status_code == 200
    q_data = query_resp.json()
    assert q_data["id"] == run_id
    assert q_data["status"] == "COMPLETED"

    # 5. Cancel endpoint
    cancel_resp = await client.post(f"/api/v1/agent/runs/{run_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"
