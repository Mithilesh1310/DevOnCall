import logging
from typing import Dict, Any, Optional
from app.services.agent.tools.base import BaseTool, ToolContext
from app.services.agent.models import ToolResult, ToolError
from app.services.agent.policies import ToolPermission
from app.services.sandbox.manager import SandboxManager
from app.services.sandbox.base import CommandType
from app.services.workspace.manager import WorkspaceManager

logger = logging.getLogger("devoncall.agent.tools.sandbox_validate")

class SandboxValidationTool(BaseTool):
    """
    Executes controlled code validation inside an isolated sandbox container.
    Requires EXECUTE_SANDBOX permission.
    """

    def __init__(self, sandbox_manager: Optional[SandboxManager] = None):
        self.sandbox_manager = sandbox_manager or SandboxManager()

    @property
    def name(self) -> str:
        return "sandbox_validate"

    @property
    def description(self) -> str:
        return "Executes controlled validation (TEST, BUILD, LINT, TYPECHECK) inside an isolated sandbox."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.EXECUTE_SANDBOX

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        workspace_id = input_params.get("workspace_id")
        command_type_raw = input_params.get("command_type", "TEST")
        runtime = input_params.get("runtime", "python")
        project_id = input_params.get("project_id", context.project_id if context else "demo-project")
        force_mock = input_params.get("force_mock", False)

        agent_run_id = context.run_id if context else None
        policy = context.policy if context else None
        db_session = context.run_context.get("db_session") if (context and context.run_context) else None

        if not workspace_id:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="INVALID_PARAMS", message="Parameter 'workspace_id' is required")
            )

        try:
            cmd_type = CommandType(command_type_raw.upper())
        except ValueError:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(
                    code="INVALID_COMMAND_TYPE",
                    message=f"Command type '{command_type_raw}' is invalid. Allowed: TEST, BUILD, LINT, TYPECHECK"
                )
            )

        # Resolve local workspace path safely
        try:
            workspace_path = str(WorkspaceManager.get_workspace_path(workspace_id))
        except Exception as ex:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="WORKSPACE_NOT_FOUND", message=f"Workspace path resolution error: {ex}")
            )

        if not db_session:
            # Fallback mock run if db_session is missing in isolated unit test
            mock_res = await self.sandbox_manager.mock_provider.run_validation(
                workspace_path=workspace_path,
                command_type=cmd_type,
                command_str=cmd_type.value,
                runtime=runtime
            )
            return ToolResult(
                success=(mock_res.status == "PASSED"),
                tool=self.name,
                data=mock_res.model_dump()
            )

        try:
            sandbox_run = await self.sandbox_manager.run_validation(
                db=db_session,
                project_id=project_id,
                workspace_id=workspace_id,
                workspace_path=workspace_path,
                command_type=cmd_type,
                agent_run_id=agent_run_id,
                runtime=runtime,
                policy=policy,
                force_mock=force_mock
            )

            is_success = sandbox_run.status in ["PASSED"]
            return ToolResult(
                success=is_success,
                tool=self.name,
                data={
                    "sandbox_run_id": sandbox_run.id,
                    "status": sandbox_run.status,
                    "exit_code": sandbox_run.exit_code,
                    "command_type": sandbox_run.command_type,
                    "provider_type": sandbox_run.provider_type,
                    "stdout": sandbox_run.stdout,
                    "stderr": sandbox_run.stderr,
                    "duration_ms": sandbox_run.duration_ms,
                    "error_message": sandbox_run.error_message
                }
            )

        except PermissionError as pe:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="PERMISSION_DENIED", message=str(pe))
            )
        except Exception as ex:
            logger.error(f"SandboxValidationTool execution failed: {ex}")
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="SANDBOX_EXECUTION_ERROR", message=str(ex))
            )
