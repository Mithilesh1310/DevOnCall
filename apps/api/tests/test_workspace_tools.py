import os
import pytest
from app.services.agent.tools.workspace_write import CreateWorkspaceTool, WriteFileTool, ApplyPatchTool
from app.services.agent.tools.base import ToolContext
from app.services.workspace import default_workspace_manager

@pytest.mark.asyncio
async def test_create_workspace_tool():
    run_id = "testrun-ws-01"
    tool = CreateWorkspaceTool()
    context = ToolContext(run_id=run_id, project_id="proj-1")

    result = await tool.execute({"base_branch": "main"}, context)
    assert result.success is True
    assert result.data["branch_name"] == f"devoncall/agent/{run_id[:8]}"
    assert os.path.exists(default_workspace_manager.get_workspace_root(run_id))

@pytest.mark.asyncio
async def test_write_file_and_apply_patch_tool():
    run_id = "testrun-ws-02"
    context = ToolContext(run_id=run_id, project_id="proj-1")

    write_tool = WriteFileTool()
    w_res = await write_tool.execute({"path": "app.py", "content": "print('Hello')\n"}, context)
    assert w_res.success is True
    assert w_res.data["lines_count"] == 1

    patch_tool = ApplyPatchTool()
    p_res = await patch_tool.execute({"path": "app.py", "patch_content": "print('Hello World')\n"}, context)
    assert p_res.success is True
    assert p_res.data["patch_applied"] is True

    # Read file back to verify content
    read_res, data, _ = default_workspace_manager.read_file_safe(run_id, "app.py")
    assert read_res is True
    assert "Hello World" in data["content"]
