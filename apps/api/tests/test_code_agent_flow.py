import pytest
from httpx import AsyncClient
from app.models.project import Project

@pytest.mark.asyncio
async def test_code_agent_end_to_end_flow(client: AsyncClient, db_session):
    # Create test project
    project = Project(
        name="demo-code-repo",
        github_owner="devoncall",
        github_repo="demo-repo",
        default_branch="main"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # 1. Trigger coding agent run
    create_res = await client.post("/api/v1/agent/runs", json={
        "project_id": project.id,
        "task": "Fix hello function greeting"
    })
    assert create_res.status_code == 201
    run_data = create_res.json()
    run_id = run_data["id"]
    assert run_data["status"] == "AWAITING_APPROVAL"

    # 2. Get agent run diff
    diff_res = await client.get(f"/api/v1/agent/runs/{run_id}/diff")
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert "files_changed" in diff_data
    assert diff_data["total_additions"] > 0

    # 3. Get agent run changes summary
    changes_res = await client.get(f"/api/v1/agent/runs/{run_id}/changes")
    assert changes_res.status_code == 200
    changes_data = changes_res.json()
    assert changes_data["run_id"] == run_id

    # 4. Approve agent run and trigger PR creation
    approve_res = await client.post(f"/api/v1/agent/runs/{run_id}/approve")
    assert approve_res.status_code == 200
    approve_data = approve_res.json()
    assert approve_data["status"] == "COMPLETED"
    assert "pull_request_url" in approve_data
    assert "https://github.com" in approve_data["pull_request_url"]
