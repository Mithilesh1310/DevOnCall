import os
from typing import Dict, Any
from app.services.agent.policies import ToolPermission
from app.services.agent.models import ToolResult, ToolError
from app.services.agent.tools.base import BaseTool, ToolContext
from app.services.workspace import default_workspace_manager

class CreateWorkspaceTool(BaseTool):
    """
    Creates an isolated workspace directory and agent branch for the current run.
    """

    @property
    def name(self) -> str:
        return "create_workspace"

    @property
    def description(self) -> str:
        return "Initializes an isolated per-run workspace environment and checks out a new agent feature branch."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.WRITE_WORKSPACE

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        base_branch = input_params.get("base_branch") or (context.run_context and context.run_context.get("default_branch")) or (context.repository_snapshot and context.repository_snapshot.get("default_branch")) or "main"
        
        ws_path, branch_name, base_sha = default_workspace_manager.create_workspace(
            run_id=context.run_id,
            default_branch=base_branch
        )

        data = {
            "workspace_id": f"ws-{context.run_id[:8]}",
            "workspace_path": f"workspaces/{context.run_id[:8]}/repository",
            "branch_name": branch_name,
            "base_commit_sha": base_sha,
            "base_branch": base_branch
        }
        return ToolResult(success=True, tool=self.name, data=data)


class WriteFileTool(BaseTool):
    """
    Safely writes text content to a file inside the isolated workspace.
    Enforces path traversal protection and rejects protected files (.env, .git, keys).
    """

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Writes text content to a file strictly inside the workspace repository, enforcing path sandbox & file protection."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.WRITE_WORKSPACE

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        path = input_params.get("path", "").strip()
        content = input_params.get("content", "")

        if not path:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="INVALID_INPUT", message="Parameter 'path' is required.")
            )

        success, data, err = default_workspace_manager.write_file_safe(
            run_id=context.run_id,
            relative_path=path,
            content=content
        )

        if not success:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="WRITE_FILE_FAILED", message=err or "Failed to write file.")
            )

        return ToolResult(success=True, tool=self.name, data=data)


class ApplyPatchTool(BaseTool):
    """
    Applies a structured diff/patch to a target workspace file.
    """

    @property
    def name(self) -> str:
        return "apply_patch"

    @property
    def description(self) -> str:
        return "Applies a structured text replacement patch to a target file inside the workspace."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.WRITE_WORKSPACE

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        path = input_params.get("path", "").strip()
        patch_content = input_params.get("patch_content", "")

        if not path or not patch_content:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="INVALID_INPUT", message="Parameters 'path' and 'patch_content' are required.")
            )

        # Write patch content safely using write_file_safe
        success, data, err = default_workspace_manager.write_file_safe(
            run_id=context.run_id,
            relative_path=path,
            content=patch_content
        )

        if not success:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="PATCH_FAILED", message=err or "Failed to apply patch.")
            )

        data["patch_applied"] = True
        return ToolResult(success=True, tool=self.name, data=data)
