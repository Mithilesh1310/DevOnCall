import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_github_status_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/github/status")
    assert response.status_code == 200
    data = response.json()
    assert "provider_type" in data
    assert "mock_enabled" in data
    assert "status" in data

@pytest.mark.asyncio
async def test_github_repos_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/github/repos")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["owner"] == "mock-owner"

@pytest.mark.asyncio
async def test_project_github_connect_and_inspect_flow(client: AsyncClient):
    # 1. Create Project
    create_resp = await client.post("/api/v1/projects", json={
        "name": "DevOnCall Demo Workload",
        "default_branch": "main"
    })
    assert create_resp.status_code == 201
    project = create_resp.json()
    project_id = project["id"]

    # 2. Connect GitHub Repository
    connect_resp = await client.post(f"/api/v1/projects/{project_id}/github/connect", json={
        "github_owner": "mock-owner",
        "github_repo": "devoncall-demo",
        "default_branch": "main"
    })
    assert connect_resp.status_code == 200
    conn_proj = connect_resp.json()
    assert conn_proj["github_owner"] == "mock-owner"
    assert conn_proj["github_repo"] == "devoncall-demo"

    # 3. Inspect Repository
    inspect_resp = await client.post(f"/api/v1/projects/{project_id}/github/inspect")
    assert inspect_resp.status_code == 200
    inspected_proj = inspect_resp.json()
    assert inspected_proj["last_indexed_commit_sha"] is not None
    assert inspected_proj["repository_snapshot"] is not None

    snapshot = inspected_proj["repository_snapshot"]
    assert snapshot["owner"] == "mock-owner"
    assert snapshot["repo"] == "devoncall-demo"
    assert len(snapshot["important_files"]) > 0

    # 4. Fetch Snapshot directly
    snap_resp = await client.get(f"/api/v1/projects/{project_id}/snapshot")
    assert snap_resp.status_code == 200
    direct_snap = snap_resp.json()
    assert direct_snap["owner"] == "mock-owner"
