from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class ToolError(BaseModel):
    code: str
    message: str

class ToolResult(BaseModel):
    success: bool
    tool: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[ToolError] = None

class ToolCallRecord(BaseModel):
    tool_name: str
    input_params: Dict[str, Any]
    success: bool
    summary: str
    started_at: datetime
    completed_at: datetime
    error: Optional[str] = None

class AgentAction(BaseModel):
    action_type: Literal["tool_call", "complete", "wait", "await_approval"]
    tool: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    summary: str
    completed: bool = False

class Observation(BaseModel):
    step: int
    tool_name: str
    result: ToolResult
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentState(BaseModel):
    run_id: str
    project_id: str
    user_task: str
    incident_id: Optional[str] = None
    status: Literal["PENDING", "RUNNING", "WAITING", "AWAITING_APPROVAL", "COMPLETED", "FAILED", "CANCELLED"] = "PENDING"
    current_goal: Optional[str] = None
    plan: List[str] = Field(default_factory=list)
    current_step: int = 0
    iteration_count: int = 0
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    observations: List[Observation] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    sandbox_runs: List[Dict[str, Any]] = Field(default_factory=list)
    validation_results: List[Dict[str, Any]] = Field(default_factory=list)
    last_validation_result: Optional[Dict[str, Any]] = None
    validation_history: List[Dict[str, Any]] = Field(default_factory=list)
    failure_analysis: Optional[Dict[str, Any]] = None
    repair_attempts: List[Dict[str, Any]] = Field(default_factory=list)
    successful_validations: List[str] = Field(default_factory=list)
    failed_validations: List[str] = Field(default_factory=list)
    current_validation: Optional[str] = None
    next_action: Optional[str] = None
    stop_reason: Optional[str] = None
    browser_runs: List[Dict[str, Any]] = Field(default_factory=list)
    browser_results: List[Dict[str, Any]] = Field(default_factory=list)
    run_context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

