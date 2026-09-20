import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.services.agent.models import AgentState, AgentAction
from app.services.agent.state import StateManager
from app.services.agent.planner import BasePlanner, MockPlanner
from app.services.agent.executor import ToolExecutor
from app.services.agent.registry import ToolRegistry, default_tool_registry
from app.services.agent.policies import AgentPolicy, default_phase3_policy, default_phase5_policy
from app.services.agent.tools.base import ToolContext

logger = logging.getLogger("devoncall.agent.runtime")

MAX_AGENT_ITERATIONS = 15

class AgentRuntime:
    """
    Controlled execution runtime loop for DevOnCall AI agent runs.
    Enforces iteration limits, policy permissions, structured observations, human approval pauses, and clean state progression.
    """

    def __init__(
        self,
        planner: Optional[BasePlanner] = None,
        registry: ToolRegistry = default_tool_registry,
        policy: AgentPolicy = default_phase5_policy
    ):
        self.planner = planner or MockPlanner()
        self.registry = registry
        self.policy = policy
        self.executor = ToolExecutor(registry=self.registry, policy=self.policy)

    async def run(self, state: AgentState, repository_snapshot: Optional[Dict[str, Any]] = None) -> AgentState:
        logger.info(f"Starting Agent Runtime loop for run_id '{state.run_id}' (Task: '{state.user_task}')")
        if state.status in ("PENDING", "AWAITING_APPROVAL"):
            state.status = "RUNNING"
        state.updated_at = datetime.now(timezone.utc)

        while state.status == "RUNNING" and state.iteration_count < MAX_AGENT_ITERATIONS:
            logger.info(f"[Run {state.run_id}] Iteration {state.iteration_count + 1}/{MAX_AGENT_ITERATIONS}, Step {state.current_step}")

            context = ToolContext(
                run_id=state.run_id,
                project_id=state.project_id,
                repository_snapshot=repository_snapshot,
                policy=self.policy,
                run_context=state.run_context
            )

            available_tools = [t.name for t in self.registry.list_tools() if self.policy.is_permission_allowed(t.permission_level)]

            # 1. Ask planner for next action
            action: AgentAction = self.planner.plan(state, available_tools)
            logger.info(f"[Run {state.run_id}] Planner action: {action.action_type} - {action.summary}")

            # 2. Handle completion action
            if action.completed or action.action_type == "complete":
                StateManager.mark_completed(state, summary=action.summary)
                break

            # 3. Handle human approval pause action
            if action.action_type == "await_approval":
                logger.info(f"[Run {state.run_id}] Pausing runtime loop for human approval gate: {action.summary}")
                state.status = "AWAITING_APPROVAL"
                state.current_goal = action.summary
                state.updated_at = datetime.now(timezone.utc)
                break

            # 4. Handle tool call action
            if action.action_type == "tool_call":
                if not action.tool:
                    StateManager.mark_failed(state, "Planner requested tool_call action but specified no tool name.")
                    break

                started_at = datetime.now(timezone.utc)
                input_params = action.input or {}

                # Execute tool via executor
                result = await self.executor.execute_tool(action.tool, input_params, context)
                completed_at = datetime.now(timezone.utc)

                # Record tool call & observation into state
                StateManager.record_tool_call(
                    state=state,
                    tool_name=action.tool,
                    input_params=input_params,
                    result=result,
                    started_at=started_at,
                    completed_at=completed_at,
                    summary=action.summary
                )

                state.current_step += 1
                state.iteration_count += 1

                # If tool failed with authorization or missing tool error, mark state failed
                if not result.success and result.error and result.error.code in ("TOOL_NOT_FOUND", "PERMISSION_DENIED"):
                    StateManager.mark_failed(state, f"Fatal tool error: {result.error.message}")
                    break
            else:
                StateManager.mark_failed(state, f"Unsupported action type '{action.action_type}' received from planner.")
                break

        # Check for iteration limit exhaustion
        if state.status == "RUNNING" and state.iteration_count >= MAX_AGENT_ITERATIONS:
            logger.warning(f"[Run {state.run_id}] Reached MAX_AGENT_ITERATIONS limit ({MAX_AGENT_ITERATIONS})")
            StateManager.mark_failed(state, f"Agent run reached maximum iteration limit ({MAX_AGENT_ITERATIONS}).")

        logger.info(f"Agent Runtime loop finished for run '{state.run_id}' with status '{state.status}'")
        return state

    async def resume_after_approval(self, state: AgentState, repository_snapshot: Optional[Dict[str, Any]] = None) -> AgentState:
        """
        Resumes agent execution after human approval is granted.
        """
        logger.info(f"Granting human approval for run_id '{state.run_id}' and resuming execution.")
        state.run_context["approved"] = True
        state.status = "RUNNING"
        return await self.run(state, repository_snapshot=repository_snapshot)
