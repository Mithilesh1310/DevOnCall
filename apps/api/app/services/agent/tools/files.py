import os
from typing import Dict, Any
from app.services.agent.policies import ToolPermission
from app.services.agent.models import ToolResult, ToolError
from app.services.agent.tools.base import BaseTool, ToolContext

class FileMetadataTool(BaseTool):
    """
    Returns file metadata (path, extension, size, type) from the repository snapshot.
    Does NOT download raw file contents.
    """

    @property
    def name(self) -> str:
        return "file_metadata"

    @property
    def description(self) -> str:
        return "Returns file metadata (path, extension, size, node type) for a specific repository file without downloading content."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        target_path = input_params.get("path", "").strip().strip("/")
        if not target_path:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="INVALID_INPUT", message="Parameter 'path' is required.")
            )

        if not context.repository_snapshot:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="SNAPSHOT_NOT_FOUND", message="No repository snapshot context is available.")
            )

        tree = context.repository_snapshot.get("tree", [])
        matched_node = None

        for node in tree:
            if node.get("path", "").lower() == target_path.lower():
                matched_node = node
                break

        if not matched_node:
            # Check important files list
            important_files = context.repository_snapshot.get("important_files", [])
            if any(f.lower() == target_path.lower() for f in important_files):
                ext = os.path.splitext(target_path)[1]
                data = {
                    "path": target_path,
                    "name": os.path.basename(target_path),
                    "extension": ext,
                    "type": "file",
                    "is_important_file": True,
                    "size": None
                }
                return ToolResult(success=True, tool=self.name, data=data)

            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="FILE_NOT_FOUND", message=f"File path '{target_path}' not found in repository tree.")
            )

        ext = os.path.splitext(matched_node.get("path", ""))[1]
        data = {
            "path": matched_node.get("path"),
            "name": matched_node.get("name"),
            "extension": ext,
            "type": matched_node.get("type"),
            "size": matched_node.get("size"),
            "is_important_file": matched_node.get("path") in context.repository_snapshot.get("important_files", [])
        }
        return ToolResult(success=True, tool=self.name, data=data)
