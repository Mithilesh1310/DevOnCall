import pytest
from app.services.agent.registry import ToolRegistry, default_tool_registry
from app.services.agent.policies import AgentPolicy, ToolPermission, default_phase2_policy
from app.services.agent.tools.base import BaseTool, ToolContext
from app.services.agent.models import ToolResult

class DummyWriteTool(BaseTool):
    @property
    def name(self) -> str:
        return "workspace_write"
    @property
    def description(self) -> str:
        return "Write to workspace"
    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.WRITE_WORKSPACE
    async def execute(self, input_params: dict, context: ToolContext) -> ToolResult:
        return ToolResult(success=True, tool=self.name, data={})

def test_default_tool_registry_contains_read_only_tools():
    tools = [t.name for t in default_tool_registry.list_tools()]
    assert "repository_info" in tools
    assert "repository_tree" in tools
    assert "file_metadata" in tools
    assert "search_repository" in tools
    assert "project_snapshot" in tools

def test_tool_registry_permission_policy_checks():
    registry = ToolRegistry()
    registry.register(DummyWriteTool())

    # Phase 2 default policy (READ_ONLY only)
    allowed, reason = registry.is_allowed("workspace_write", default_phase2_policy)
    assert allowed is False
    assert "requires permission 'WRITE_WORKSPACE'" in reason

def test_unknown_tool_rejection():
    allowed, reason = default_tool_registry.is_allowed("shell.execute", default_phase2_policy)
    assert allowed is False
    assert "is not registered" in reason
