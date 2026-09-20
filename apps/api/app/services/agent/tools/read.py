from typing import Dict, Any, Optional
from app.services.agent.policies import ToolPermission
from app.services.agent.models import ToolResult, ToolError
from app.services.agent.tools.base import BaseTool, ToolContext
from app.services.workspace import default_workspace_manager

class ReadFileTool(BaseTool):
    """
    Reads workspace file content safely within specified line ranges.
    Rejects path traversal and sensitive/credential files (.env, keys).
    """

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Reads line-bounded text content of a workspace file. Rejects sensitive credential files."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        path = input_params.get("path", "").strip()
        if not path:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="INVALID_INPUT", message="Parameter 'path' is required.")
            )

        start_line = input_params.get("start_line")
        end_line = input_params.get("end_line")

        success, data, err = default_workspace_manager.read_file_safe(
            run_id=context.run_id,
            relative_path=path,
            start_line=start_line,
            end_line=end_line
        )

        if not success:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="READ_FILE_FAILED", message=err or "Failed to read file.")
            )

        return ToolResult(success=True, tool=self.name, data=data)
