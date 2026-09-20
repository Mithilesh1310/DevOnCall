import logging
import time
from typing import Dict, Any
from app.services.agent.models import ToolResult, ToolError
from app.services.agent.registry import ToolRegistry, default_tool_registry
from app.services.agent.tools.base import ToolContext
from app.services.agent.policies import AgentPolicy, default_phase2_policy

logger = logging.getLogger("devoncall.agent.executor")

class ToolExecutor:
    """
    Executes selected agent tools within a controlled environment.
    Enforces permission checks, context boundaries, and returns structured ToolResult payloads.
    """

    def __init__(self, registry: ToolRegistry = default_tool_registry, policy: AgentPolicy = default_phase2_policy):
        self.registry = registry
        self.policy = policy

    async def execute_tool(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        context: ToolContext
    ) -> ToolResult:
        logger.info(f"Executor received tool request '{tool_name}' for run {context.run_id}")

        # 1. Resolve tool from registry
        tool = self.registry.get(tool_name)
        if not tool:
            logger.warning(f"Rejected unregistered tool invocation '{tool_name}'")
            return ToolResult(
                success=False,
                tool=tool_name,
                error=ToolError(code="TOOL_NOT_FOUND", message=f"Tool '{tool_name}' is not registered in ToolRegistry.")
            )

        # 2. Check permission policy
        allowed, reason = self.registry.is_allowed(tool_name, self.policy)
        if not allowed:
            logger.warning(f"Permission denied for tool '{tool_name}': {reason}")
            return ToolResult(
                success=False,
                tool=tool_name,
                error=ToolError(code="PERMISSION_DENIED", message=reason)
            )

        # 3. Execute tool safely
        start_time = time.time()
        try:
            result = await tool.execute(input_params, context)
            elapsed = time.time() - start_time
            logger.info(f"Tool '{tool_name}' executed in {elapsed:.3f}s (Success: {result.success})")
            return result
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error(f"Execution failure in tool '{tool_name}': {exc}", exc_info=True)
            return ToolResult(
                success=False,
                tool=tool_name,
                error=ToolError(code="TOOL_EXECUTION_ERROR", message=f"Internal tool error: {str(exc)}")
            )
