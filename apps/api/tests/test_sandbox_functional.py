import pytest
from httpx import AsyncClient
from app.services.sandbox import MockSandboxProvider, CommandType, SandboxStatus
from app.services.agent.tools.sandbox_tool import SandboxValidationTool

@pytest.mark.asyncio
async def test_mock_sandbox_provider_scenarios():
    provider = MockSandboxProvider()

    # PASS Scenario
    res_pass = await provider.run_validation("ws-1", CommandType.TEST, "pytest")
    assert res_pass.status == SandboxStatus.PASSED
    assert res_pass.exit_code == 0
    assert "5 passed" in res_pass.stdout

    # FAIL Scenario
    res_fail = await provider.run_validation("ws-1", CommandType.TEST, "pytest FAIL")
    assert res_fail.status == SandboxStatus.FAILED
    assert res_fail.exit_code == 1
    assert "AssertionError" in res_fail.stderr

    # TIMEOUT Scenario
    res_timeout = await provider.run_validation("ws-1", CommandType.TEST, "pytest TIMEOUT")
    assert res_timeout.status == SandboxStatus.TIMED_OUT
    assert res_timeout.exit_code == -1

    # ERROR Scenario
    res_err = await provider.run_validation("ws-1", CommandType.TEST, "pytest ERROR")
    assert res_err.status == SandboxStatus.ERROR
    assert res_err.exit_code == 127

from app.services.agent.tools.base import ToolContext

@pytest.mark.asyncio
async def test_sandbox_validation_tool_execution():
    tool = SandboxValidationTool(sandbox_manager=None)
    assert tool.name == "sandbox_validate"
    assert tool.permission_level.value == "EXECUTE_SANDBOX"

    context = ToolContext(run_id="test-run-101", project_id="demo-project")

    # Execute tool with PASS command
    result = await tool.execute({
        "workspace_id": "ws-demo-run",
        "command_type": "TEST",
        "runtime": "python"
    }, context=context)

    assert result.success is True
    assert result.data["status"] == "PASSED"

@pytest.mark.asyncio
async def test_sandbox_api_endpoints(client: AsyncClient):
    # 1. Create sandbox run via API endpoint
    res_create = await client.post("/api/v1/sandbox/runs", json={
        "project_id": "demo-project",
        "workspace_id": "ws-test-sandbox",
        "command_type": "TEST",
        "runtime": "python",
        "force_mock": True
    })
    assert res_create.status_code == 201
    data = res_create.json()
    assert "id" in data
    assert data["command_type"] == "TEST"
    assert data["status"] == "PASSED"
    run_id = data["id"]

    # 2. Get single sandbox run by ID
    res_get = await client.get(f"/api/v1/sandbox/runs/{run_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == run_id

    # 3. List sandbox runs
    res_list = await client.get("/api/v1/sandbox/runs")
    assert res_list.status_code == 200
    runs = res_list.json()
    assert len(runs) >= 1
    assert any(r["id"] == run_id for r in runs)
