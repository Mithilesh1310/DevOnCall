import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.services.agent.models import AgentState, ToolCallRecord, Observation, ToolResult

logger = logging.getLogger("devoncall.agent.state")

class StateManager:
    """
    Manages state mutations, serialization, and history tracking for AgentState instances.
    """

    @staticmethod
    def create_initial_state(
        run_id: str,
        project_id: str,
        user_task: str,
        incident_id: Optional[str] = None
    ) -> AgentState:
        return AgentState(
            run_id=run_id,
            project_id=project_id,
            user_task=user_task,
            incident_id=incident_id,
            status="PENDING",
            current_goal=f"Investigating task: '{user_task}'",
            plan=[],
            current_step=0,
            iteration_count=0
        )

    @staticmethod
    def record_tool_call(
        state: AgentState,
        tool_name: str,
        input_params: Dict[str, Any],
        result: ToolResult,
        started_at: datetime,
        completed_at: datetime,
        summary: str
    ) -> None:
        record = ToolCallRecord(
            tool_name=tool_name,
            input_params=input_params,
            success=result.success,
            summary=summary,
            started_at=started_at,
            completed_at=completed_at,
            error=result.error.message if result.error else None
        )
        state.tool_calls.append(record)

        obs = Observation(
            step=state.current_step,
            tool_name=tool_name,
            result=result,
            timestamp=completed_at
        )
        state.observations.append(obs)
        state.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def mark_completed(state: AgentState, summary: str = "Run completed") -> None:
        state.status = "COMPLETED"
        state.current_goal = summary
        state.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def mark_failed(state: AgentState, reason: str) -> None:
        state.status = "FAILED"
        state.errors.append(reason)
        state.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def mark_cancelled(state: AgentState) -> None:
        state.status = "CANCELLED"
        state.updated_at = datetime.now(timezone.utc)
