import logging
from typing import Dict, List, Optional, Tuple
from app.services.agent.tools.base import BaseTool
from app.services.agent.policies import AgentPolicy, ToolPermission, default_phase3_policy
from app.services.agent.tools.repository import RepositoryInfoTool, RepositoryTreeTool, ProjectSnapshotTool
from app.services.agent.tools.files import FileMetadataTool
from app.services.agent.tools.search import SearchRepositoryTool
from app.services.agent.tools.read import ReadFileTool
from app.services.agent.tools.workspace_write import CreateWorkspaceTool, WriteFileTool, ApplyPatchTool
from app.services.agent.tools.git_tools import GitDiffTool, GitStatusTool, GitCreateBranchTool, GitCommitTool, CreatePullRequestTool
from app.services.agent.tools.sandbox_tool import SandboxValidationTool
from app.services.agent.tools.browser_tool import BrowserValidationTool
from app.services.agent.tools.brain_tool import ProjectBrainQueryTool
from app.services.agent.tools.observability_tools import (
    ProductionIncidentSearchTool,
    ProductionIncidentDetailsTool,
    ProductionIncidentCorrelateTool,
)
from app.services.agent.tools.deployment_tools import (
    ReleaseCandidateStatusTool,
    CanaryVerificationDetailsTool,
    DeploymentAuditLogTool,
)

logger = logging.getLogger("devoncall.agent.registry")

class ToolRegistry:
    """
    Central tool registry for DevOnCall Agent Runtime.
    Manages available tools, resolves tool instances by name, and verifies permission policies.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            logger.warning(f"Overwriting tool registration for '{tool.name}'")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool '{tool.name}' (Permission: {tool.permission_level.value})")

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def is_allowed(self, name: str, policy: AgentPolicy = default_phase3_policy) -> Tuple[bool, str]:
        tool = self.get(name)
        if not tool:
            return False, f"Tool '{name}' is not registered in the tool registry."

        if not policy.is_permission_allowed(tool.permission_level):
            return False, f"Tool '{name}' requires permission '{tool.permission_level.value}' which is not allowed by current agent policy."

        return True, "Tool authorization approved."

def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    # Register Phase 2, 3, 5, 7, 10, 11, & 12 Tools
    registry.register(RepositoryInfoTool())
    registry.register(RepositoryTreeTool())
    registry.register(ProjectSnapshotTool())
    registry.register(FileMetadataTool())
    registry.register(SearchRepositoryTool())
    registry.register(ReadFileTool())
    registry.register(CreateWorkspaceTool())
    registry.register(WriteFileTool())
    registry.register(ApplyPatchTool())
    registry.register(GitDiffTool())
    registry.register(GitStatusTool())
    registry.register(GitCreateBranchTool())
    registry.register(GitCommitTool())
    registry.register(CreatePullRequestTool())
    registry.register(SandboxValidationTool())
    registry.register(BrowserValidationTool())
    registry.register(ProjectBrainQueryTool())
    registry.register(ProductionIncidentSearchTool())
    registry.register(ProductionIncidentDetailsTool())
    registry.register(ProductionIncidentCorrelateTool())
    registry.register(ReleaseCandidateStatusTool())
    registry.register(CanaryVerificationDetailsTool())
    registry.register(DeploymentAuditLogTool())
    return registry


default_tool_registry = create_default_registry()
