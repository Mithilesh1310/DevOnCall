from typing import Any, Dict, Optional
from app.services.agent.tools.base import BaseTool, ToolContext
from app.services.agent.policies import ToolPermission
from app.services.agent.models import ToolResult, ToolError
from app.services.browser import BrowserManager, get_scenario, PREDEFINED_SCENARIOS, BrowserScenario

class BrowserValidationTool(BaseTool):
    """
    Tool allowing the agent runtime to trigger controlled browser UI verification.
    Requires BROWSER_SANDBOX permission.
    """

    @property
    def name(self) -> str:
        return "browser_validate"

    @property
    def description(self) -> str:
        return "Executes structured browser UI scenario verification against an allowlisted base URL."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.BROWSER_SANDBOX

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        project_id = input_params.get("project_id") or getattr(context, "project_id", "default-project")
        workspace_id = input_params.get("workspace_id") or f"ws-{project_id[:8]}"
        scenario_id = input_params.get("scenario_id", "login-smoke")
        base_url = input_params.get("base_url", "http://localhost:3000")
        use_mock = input_params.get("use_mock", True)

        scenario = get_scenario(scenario_id)
        if not scenario:
            scenario = PREDEFINED_SCENARIOS.get("login-smoke")

        if scenario:
            scenario = BrowserScenario(
                id=scenario.id,
                name=scenario.name,
                description=scenario.description,
                base_url=base_url,
                steps=scenario.steps
            )

        manager = BrowserManager(use_mock=use_mock)
        result = await manager.execute_browser_validation(
            scenario=scenario,
            project_id=project_id,
            workspace_id=workspace_id,
            agent_run_id=getattr(context, "run_id", "run-default")
        )


        return ToolResult(
            success=(result.status.value == "PASSED"),
            tool=self.name,
            data={
                "browser_run_id": result.id,
                "status": result.status.value,
                "provider_type": result.provider_type,
                "scenario_id": result.scenario_id,
                "passed_steps": result.passed_steps,
                "failed_steps": result.failed_steps,
                "error_type": result.error_type.value if result.error_type else None,
                "error_message": result.error_message,
                "suspected_file": result.suspected_file,
                "screenshot_paths": result.screenshot_paths
            },
            error=ToolError(code=result.error_type.value, message=result.error_message) if result.error_type else None
        )
