from typing import Dict, Any, Optional, List
from app.services.agent.policies import ToolPermission
from app.services.agent.models import ToolResult, ToolError
from app.services.agent.tools.base import BaseTool, ToolContext

class RepositoryInfoTool(BaseTool):
    """
    Returns general metadata, languages, framework detections, and statistics for the connected repository.
    """

    @property
    def name(self) -> str:
        return "repository_info"

    @property
    def description(self) -> str:
        return "Returns repository identity, branch, latest commit SHA, languages, detected frameworks, and file statistics."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        if not context.repository_snapshot:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="SNAPSHOT_NOT_FOUND", message="No repository snapshot context is available for this project.")
            )

        snapshot = context.repository_snapshot
        data = {
            "owner": snapshot.get("owner"),
            "repo": snapshot.get("repo"),
            "default_branch": snapshot.get("default_branch"),
            "commit_sha": snapshot.get("commit_sha"),
            "url": snapshot.get("url"),
            "total_files": snapshot.get("total_files"),
            "total_directories": snapshot.get("total_directories"),
            "detected_languages": snapshot.get("detected_languages", []),
            "detections": snapshot.get("detections", [])
        }
        return ToolResult(success=True, tool=self.name, data=data)


class RepositoryTreeTool(BaseTool):
    """
    Returns normalized repository tree entries filtered by optional path or max_depth.
    """

    @property
    def name(self) -> str:
        return "repository_tree"

    @property
    def description(self) -> str:
        return "Returns normalized repository tree hierarchy filtered by optional path or max_depth."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        if not context.repository_snapshot:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="SNAPSHOT_NOT_FOUND", message="No repository snapshot context is available.")
            )

        filter_path = input_params.get("path", "").strip().strip("/")
        max_depth = input_params.get("max_depth")

        tree = context.repository_snapshot.get("tree", [])

        if filter_path:
            # Filter nodes under specified directory path
            tree = [node for node in tree if node.get("path", "").startswith(filter_path)]

        if max_depth is not None and isinstance(max_depth, int):
            tree = [node for node in tree if len(node.get("path", "").split("/")) <= max_depth]

        data = {
            "filtered_path": filter_path or "/",
            "total_items": len(tree),
            "tree": tree
        }
        return ToolResult(success=True, tool=self.name, data=data)


class ProjectSnapshotTool(BaseTool):
    """
    Returns the complete structured RepositorySnapshot payload.
    """

    @property
    def name(self) -> str:
        return "project_snapshot"

    @property
    def description(self) -> str:
        return "Returns the full deterministic RepositorySnapshot payload containing tree, files, and framework detections."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        if not context.repository_snapshot:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="SNAPSHOT_NOT_FOUND", message="No repository snapshot context is available.")
            )

        return ToolResult(success=True, tool=self.name, data=context.repository_snapshot)
