import os
import pytest
from app.services.agent.tools.read import ReadFileTool
from app.services.agent.tools.base import ToolContext
from app.services.workspace import default_workspace_manager

@pytest.mark.asyncio
async def test_read_file_tool_success(tmp_path):
    run_id = "testrun-read-01"
    ws_root = default_workspace_manager.get_workspace_root(run_id)
    os.makedirs(ws_root, exist_ok=True)

    file_path = os.path.join(ws_root, "sample.py")
    lines = [f"line {i}\n" for i in range(1, 20)]
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    tool = ReadFileTool()
    context = ToolContext(run_id=run_id, project_id="proj-1")

    # Read line 5 to 10
    result = await tool.execute({"path": "sample.py", "start_line": 5, "end_line": 10}, context)
    assert result.success is True
    assert result.data["start_line"] == 5
    assert result.data["end_line"] == 10
    assert result.data["total_lines"] == 19
    assert "line 5" in result.data["content"]
    assert "line 10" in result.data["content"]

@pytest.mark.asyncio
async def test_read_file_tool_protected_file():
    run_id = "testrun-read-02"
    tool = ReadFileTool()
    context = ToolContext(run_id=run_id, project_id="proj-1")

    result = await tool.execute({"path": ".env"}, context)
    assert result.success is False
    assert result.error.code == "READ_FILE_FAILED"
    assert "protected" in result.error.message.lower()
